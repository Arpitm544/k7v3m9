#!/bin/sh
set -eu
# Run with both local development servers already started.
python3 - <<'PY'
import json
import urllib.request
for port in (8000, 5173):
    origin = f'http://127.0.0.1:{port}'
    for route in ('/api/health', '/api/metadata', '/api/decision?date=2026-01-31&cutoff=09:00', '/api/accuracy'):
        with urllib.request.urlopen(origin + route, timeout=15) as response:
            result = json.load(response)
            assert response.status == 200
            if '/decision' in route:
                assert result['delivery_date'] == '2026-02-01'
            if '/accuracy' in route:
                assert result['metrics']['matched_hours'] == 744
    print(f'PASS: {origin}, all API routes')
with urllib.request.urlopen('http://127.0.0.1:5173', timeout=15) as response:
    assert b'Wind Desk' in response.read()
print('PASS: frontend HTML')
PY
