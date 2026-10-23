"""Download the assignment's public Elexon data into a reproducible snapshot.
Run from the repository root: python scripts/fetch_data.py
"""
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import time
import urllib.parse
import urllib.request

BASE = 'https://data.elexon.co.uk/bmrs/api/v1/datasets/'
OUT = Path(__file__).resolve().parents[1] / 'backend' / 'data'


def fetch(job):
    dataset, day = job
    if dataset == 'WINDFOR':
        params = {'publishDateTimeFrom': day.isoformat() + 'T00:00Z',
                  'publishDateTimeTo': (day + dt.timedelta(days=1)).isoformat() + 'T00:00Z'}
    else:
        params = {'settlementDateFrom': day.isoformat(), 'settlementDateTo': day.isoformat(), 'fuelType': 'WIND'}
    url = BASE + dataset + '/stream?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'WindDeskAssignment/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                rows = json.load(response)
            if not isinstance(rows, list):
                raise ValueError(f'Unexpected response for {url}')
            print(f'{dataset} {day}: {len(rows)} records', flush=True)
            return dataset, rows, url
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)


def days(first, last):
    while first <= last:
        yield first
        first += dt.timedelta(days=1)


def main():
    jobs = [('WINDFOR', day) for day in days(dt.date(2025, 12, 30), dt.date(2026, 1, 31))]
    jobs += [('FUELHH', day) for day in days(dt.date(2026, 1, 2), dt.date(2026, 2, 1))]
    collected = {'WINDFOR': [], 'FUELHH': []}
    urls = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for dataset, rows, url in pool.map(fetch, jobs):
            collected[dataset].extend(rows)
            urls.append(url)
    counts = {}
    normalized = {}
    duplicates = {}
    conflicts = {}
    for dataset, rows in collected.items():
        unique = {}
        duplicates[dataset] = 0
        conflicts[dataset] = 0
        for row in rows:
            if dataset == 'FUELHH' and row.get('fuelType') != 'WIND':
                continue
            # Preserve both target and publication time. Never collapse revisions.
            record = {key: row[key] for key in ['startTime', 'publishTime', 'generation']}
            value = record['generation']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not __import__('math').isfinite(value):
                raise ValueError(f'Invalid generation: {record}')
            key = (record['startTime'], record['publishTime'])
            if key in unique:
                if unique[key] != record:
                    conflicts[dataset] += 1
                    raise ValueError(f'Conflicting duplicate: {dataset} {key}')
                duplicates[dataset] += 1
            unique[key] = record
        normalized[dataset] = sorted(unique.values(), key=lambda r: (r['startTime'], r['publishTime']))
        counts[dataset] = len(normalized[dataset])
    cadence = sorted({r['startTime'][14:16] for r in normalized['WINDFOR']})
    if cadence != ['00']:
        raise ValueError(f'Forecast cadence changed; review hourly aggregation: {cadence}')
    payload = json.dumps(normalized, separators=(',', ':'), sort_keys=True).encode()
    manifest = {
        'downloaded_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'sha256': hashlib.sha256(payload).hexdigest(), 'records': counts,
        'exact_duplicates_removed': duplicates, 'conflicting_duplicates': conflicts,
        'decision_dates': ['2026-01-01', '2026-01-31'],
        'delivery_dates': ['2026-01-02', '2026-02-01'],
        'forecast_resolution_minutes': 60, 'actual_resolution_minutes': 30,
        'comparison': 'Hourly forecast against mean of both actual half-hours; incomplete hours excluded.',
        'units': 'MW', 'sources': urls,
    }
    # Build everything in memory first so upstream failures preserve the previous snapshot.
    OUT.mkdir(parents=True, exist_ok=True)
    snapshot = OUT / 'snapshot.json.gz'
    temp = OUT / 'snapshot.json.gz.tmp'
    with gzip.open(temp, 'wb') as stream:
        stream.write(payload)
    temp.replace(snapshot)
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Saved {counts}; compressed bytes: {snapshot.stat().st_size}', flush=True)


if __name__ == '__main__':
    main()
