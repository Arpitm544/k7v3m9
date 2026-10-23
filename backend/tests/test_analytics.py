from datetime import date, time
import math
import pytest
from backend.app.analytics import Analytics, metrics, parse_timestamp


def forecast(value, published='2026-01-01T08:00:00Z', start='2026-01-02T00:00:00Z'):
    return {'startTime': start, 'publishTime': published, 'generation': value}


def actual(value, start='2026-01-02T00:00:00Z'):
    return {'startTime': start, 'publishTime': '2026-01-03T00:00:00Z', 'generation': value}


def test_asof_selection_ignores_later_revision_and_includes_exact_cutoff():
    engine = Analytics({'WINDFOR': [forecast(100), forecast(120, '2026-01-01T09:00:00Z'), forecast(999, '2026-01-01T09:01:00Z')], 'FUELHH': []})
    result = engine.decision(date(2026, 1, 1), time(9))
    assert result['points'][0]['forecast_mw'] == 120
    assert result['points'][0]['publish_time'] == '2026-01-01T09:00:00Z'
    assert result['points'][0]['lead_time_hours'] == 15


def test_hourly_actual_requires_both_half_hours_and_preserves_zero():
    engine = Analytics({'WINDFOR': [forecast(100)], 'FUELHH': [actual(0), actual(80, '2026-01-02T00:30:00Z')]})
    point = engine.decision(date(2026, 1, 1), time(9))['points'][0]
    assert point['actual_mw'] == 40
    assert point['error_mw'] == 60
    assert point['actual_half_hours'] == 2
    missing = Analytics({'WINDFOR': [forecast(100)], 'FUELHH': [actual(0)]}).decision(date(2026, 1, 1), time(9))
    assert missing['points'][0]['actual_mw'] is None
    assert missing['metrics']['matched_hours'] == 0
    assert missing['metrics']['mae_mw'] is None


def test_latest_actual_publication_is_used_once():
    revision = actual(120)
    revision['publishTime'] = '2026-01-04T00:00:00Z'
    engine = Analytics({'WINDFOR': [forecast(100)], 'FUELHH': [actual(0), revision, actual(80, '2026-01-02T00:30:00Z')]})
    result = engine.decision(date(2026, 1, 1), time(9))
    assert result['points'][0]['actual_mw'] == 100
    assert result['metrics']['matched_hours'] == 1
    assert result['metrics']['coverage_pct'] == pytest.approx(100/24)


def test_missing_eligible_forecast_is_not_filled_from_future():
    engine = Analytics({'WINDFOR': [forecast(999, '2026-01-01T09:01:00Z')], 'FUELHH': []})
    result = engine.decision(date(2026, 1, 1), time(9))
    assert result['points'][0]['forecast_mw'] is None
    assert result['metrics']['forecast_energy_mwh'] is None
    assert result['metrics']['energy_complete'] is False


def test_each_target_selects_its_own_eligible_publication():
    engine = Analytics({'WINDFOR': [forecast(100), forecast(200, '2026-01-01T08:30:00Z', '2026-01-02T01:00:00Z')], 'FUELHH': []})
    result = engine.decision(date(2026, 1, 1), time(9))
    assert [p['forecast_mw'] for p in result['points'][:2]] == [100, 200]
    assert result['publication_min'] == '2026-01-01T08:00:00Z'
    assert result['publication_max'] == '2026-01-01T08:30:00Z'
    assert result['oldest_forecast_age_hours'] == 1


def test_hand_calculated_metrics_and_hourly_energy():
    points = [{'forecast_mw': 100, 'actual_mw': 80, 'error_mw': 20}, {'forecast_mw': 60, 'actual_mw': 100, 'error_mw': -40}, {'forecast_mw': None, 'actual_mw': 100, 'error_mw': None}]
    result = metrics(points)
    assert result['mae_mw'] == 30
    assert result['rmse_mw'] == math.sqrt(1000)
    assert result['bias_mw'] == -10
    assert result['forecast_energy_mwh'] == 160
    assert result['matched_hours'] == 2
    assert result['coverage_pct'] == pytest.approx(200/3)
    assert result['energy_complete'] is False


def test_range_metrics_weight_intervals_not_days():
    engine = Analytics({'WINDFOR': [forecast(100), forecast(200, start='2026-01-03T00:00:00Z'), forecast(300, start='2026-01-03T01:00:00Z')], 'FUELHH': [actual(0), actual(0, '2026-01-02T00:30:00Z'), actual(0, '2026-01-03T00:00:00Z'), actual(0, '2026-01-03T00:30:00Z'), actual(0, '2026-01-03T01:00:00Z'), actual(0, '2026-01-03T01:30:00Z')]})
    result = engine.accuracy(date(2026, 1, 1), date(2026, 1, 2), time(9))
    assert result['metrics']['mae_mw'] == 200
    assert result['metrics']['expected_hours'] == 48
    assert sum(b['count'] for b in result['distribution']) == 3


@pytest.mark.parametrize('day,delivery', [(date(2026, 1, 1), '2026-01-02'), (date(2026, 1, 31), '2026-02-01')])
def test_decision_boundaries(day, delivery):
    result = Analytics({'WINDFOR': [], 'FUELHH': []}).decision(day, time(9))
    assert result['delivery_date'] == delivery
    assert len(result['points']) == 24
    assert result['points'][0]['start_time'] == delivery + 'T00:00:00Z'
    assert result['points'][-1]['start_time'] == delivery + 'T23:00:00Z'


def test_timezone_normalization_and_naive_rejection():
    assert parse_timestamp('2026-01-01T10:00:00+01:00') == parse_timestamp('2026-01-01T09:00:00Z')
    with pytest.raises(ValueError):
        parse_timestamp('2026-01-01T09:00:00')


def test_conflicting_forecast_keys_fail_instead_of_arbitrary_selection():
    with pytest.raises(ValueError):
        Analytics({'WINDFOR': [forecast(100), forecast(200)], 'FUELHH': []})
