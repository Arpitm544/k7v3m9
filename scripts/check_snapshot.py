"""Independent audit: raw snapshot completeness, no-lookahead selection, and scores."""
from collections import Counter
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import json
import math
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'backend/data/manifest.json').read_text())
with gzip.open(root / 'backend/data/snapshot.json.gz', 'rb') as stream:
    payload = stream.read()
assert hashlib.sha256(payload).hexdigest() == manifest['sha256']
snapshot = json.loads(payload)
actuals = {r['startTime']: r['generation'] for r in snapshot['FUELHH']}
assert len(actuals) == len(snapshot['FUELHH']) == 1488
assert all(v == 1 for v in Counter((r['startTime'], r['publishTime']) for r in snapshot['WINDFOR']).values())
errors = []
for i in range(31):
    day = date(2026, 1, 1) + timedelta(days=i)
    cutoff = day.isoformat() + 'T09:00:00Z'
    delivery = day + timedelta(days=1)
    for hour in range(24):
        target = datetime(delivery.year, delivery.month, delivery.day, hour, tzinfo=timezone.utc)
        key = target.strftime('%Y-%m-%dT%H:%M:%SZ')
        half = (target + timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        eligible = [r for r in snapshot['WINDFOR'] if r['startTime'] == key and r['publishTime'] <= cutoff]
        assert eligible, f'No forecast: {key}'
        chosen = max(eligible, key=lambda r: r['publishTime'])
        assert chosen['publishTime'] <= cutoff
        actual = (actuals[key] + actuals[half]) / 2
        errors.append(chosen['generation'] - actual)
assert len(errors) == 744
mae = sum(map(abs, errors)) / len(errors)
rmse = math.sqrt(sum(e*e for e in errors) / len(errors))
bias = sum(errors) / len(errors)
assert math.isclose(mae, 2038.9126344086021)
assert math.isclose(rmse, 2504.758652899355)
assert math.isclose(bias, 1747.8870967741937)
print(f'PASS: checksum, unique records, 1488 half-hours, 744 eligible pairs. MAE={mae:.2f} MW; RMSE={rmse:.2f} MW; bias={bias:+.2f} MW')
