from fastapi.testclient import TestClient
import pytest
from backend.app.main import app

client = TestClient(app)


def test_real_snapshot_health_and_metadata():
    assert client.get('/api/health').json()['status'] == 'ok'
    metadata = client.get('/api/metadata').json()
    assert metadata['manifest']['records']['FUELHH'] == 1488
    assert metadata['quality_at_default_cutoff']['matched_hours'] == 744
    assert metadata['manifest']['forecast_resolution_minutes'] == 60


def test_real_snapshot_has_no_lookahead_at_any_january_cutoff():
    from backend.app.main import repository
    from backend.app.analytics import parse_timestamp
    from datetime import date, time
    engine, _ = repository()
    for hour in [0, 9, 23]:
        result = engine.accuracy(date(2026, 1, 1), date(2026, 1, 31), time(hour))
        assert result['metrics']['expected_hours'] == 744
        for day in range(1, 32):
            selected = engine.decision(date(2026, 1, day), time(hour))
            for point in selected['points']:
                if point['publish_time']:
                    assert parse_timestamp(point['publish_time']) <= parse_timestamp(selected['as_of'])


def test_api_happy_path_and_month_boundary():
    response = client.get('/api/decision?date=2026-01-31&cutoff=09:00')
    assert response.status_code == 200
    result = response.json()
    assert result['delivery_date'] == '2026-02-01'
    assert result['metrics']['matched_hours'] == 24
    result = client.get('/api/accuracy?from=2026-01-01&to=2026-01-31').json()
    assert result['metrics']['matched_hours'] == 744
    assert result['metrics']['coverage_pct'] == 100
    assert result['retrospective'] is True


@pytest.mark.parametrize('path', ['/api/decision?date=2025-12-31', '/api/decision?date=2026-02-01', '/api/decision?date=bad', '/api/decision?date=2026-01-01&cutoff=25:00', '/api/decision?date=2026-01-01&cutoff=09:00:30', '/api/decision?date=2026-01-01&cutoff=9:00', '/api/accuracy?from=2026-01-31&to=2026-01-01', '/api/accuracy?from=2026-02-01'])
def test_reject_invalid_requests(path):
    assert client.get(path).status_code == 422
