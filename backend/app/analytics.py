"""Pure forecast selection and scoring. All errors use forecast minus actual."""
from bisect import bisect_right
from datetime import date, datetime, time, timedelta, timezone
import math
from zoneinfo import ZoneInfo

LONDON = ZoneInfo('Europe/London')
FIRST = date(2026, 1, 1)
LAST = date(2026, 1, 31)


def parse_timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return parsed.astimezone(timezone.utc)


def iso(value):
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def metrics(points, expected=None):
    paired = [p for p in points if p['error_mw'] is not None]
    errors = [p['error_mw'] for p in paired]
    n = len(errors)
    expected = len(points) if expected is None else expected
    forecasts = [p['forecast_mw'] for p in points if p['forecast_mw'] is not None]
    actuals = [p['actual_mw'] for p in points if p['actual_mw'] is not None]
    return {
        'mae_mw': sum(abs(e) for e in errors) / n if n else None,
        'rmse_mw': math.sqrt(sum(e * e for e in errors) / n) if n else None,
        'bias_mw': sum(errors) / n if n else None,
        'matched_hours': n, 'expected_hours': expected,
        'forecast_hours': len(forecasts), 'actual_hours': len(actuals),
        'coverage_pct': n / expected * 100 if expected else 0,
        'forecast_average_mw': sum(forecasts) / len(forecasts) if forecasts else None,
        # Each comparison interval is one hour: MW × 1 h = MWh.
        'forecast_energy_mwh': sum(forecasts) if forecasts else None,
        'actual_energy_mwh': sum(actuals) if actuals else None,
        'energy_complete': len(forecasts) == expected and len(actuals) == expected,
        'worst_absolute_error_mw': max(map(abs, errors)) if n else None,
    }


class Analytics:
    def __init__(self, snapshot):
        self.forecasts = {}
        for row in snapshot['WINDFOR']:
            target = parse_timestamp(row['startTime'])
            published = parse_timestamp(row['publishTime'])
            self.forecasts.setdefault(target, []).append((published, row['generation']))
        for rows in self.forecasts.values():
            rows.sort()
            if len({p for p, _ in rows}) != len(rows):
                raise ValueError('Duplicate forecast target/publication keys in snapshot')
        self.publications = {target: [p for p, _ in rows] for target, rows in self.forecasts.items()}
        self.actuals = {}
        for row in snapshot['FUELHH']:
            target = parse_timestamp(row['startTime'])
            publication = parse_timestamp(row['publishTime'])
            if target not in self.actuals or publication > self.actuals[target][0]:
                self.actuals[target] = (publication, row['generation'])

    def decision(self, day, cutoff):
        as_of = datetime.combine(day, cutoff, LONDON).astimezone(timezone.utc)
        delivery = day + timedelta(days=1)
        start = datetime.combine(delivery, time(), LONDON).astimezone(timezone.utc)
        end = datetime.combine(delivery + timedelta(days=1), time(), LONDON).astimezone(timezone.utc)
        points = []
        target = start
        while target < end:
            forecasts = self.forecasts.get(target, [])
            index = bisect_right(self.publications.get(target, []), as_of) - 1
            chosen = forecasts[index] if index >= 0 else None
            halves = [self.actuals.get(target), self.actuals.get(target + timedelta(minutes=30))]
            actual = sum(r[1] for r in halves) / 2 if all(r is not None for r in halves) else None
            forecast = chosen[1] if chosen else None
            points.append({
                'start_time': iso(target), 'forecast_mw': forecast, 'actual_mw': actual,
                'publish_time': iso(chosen[0]) if chosen else None,
                'error_mw': forecast - actual if forecast is not None and actual is not None else None,
                'forecast_age_hours': (as_of - chosen[0]).total_seconds() / 3600 if chosen else None,
                'lead_time_hours': (target - chosen[0]).total_seconds() / 3600 if chosen else None,
                'actual_half_hours': sum(r is not None for r in halves),
            })
            target += timedelta(hours=1)
        publication_times = sorted({p['publish_time'] for p in points if p['publish_time']})
        return {
            'decision_date': day.isoformat(), 'delivery_date': delivery.isoformat(), 'as_of': iso(as_of),
            'cutoff': cutoff.strftime('%H:%M'), 'timezone': 'Europe/London',
            'points': points, 'metrics': metrics(points),
            'publication_min': publication_times[0] if publication_times else None,
            'publication_max': publication_times[-1] if publication_times else None,
            'oldest_forecast_age_hours': max((p['forecast_age_hours'] for p in points if p['forecast_age_hours'] is not None), default=None),
        }

    def accuracy(self, first, last, cutoff):
        daily = []
        all_points = []
        day = first
        while day <= last:
            result = self.decision(day, cutoff)
            daily.append({'decision_date': result['decision_date'], 'delivery_date': result['delivery_date'], **result['metrics']})
            all_points.extend(result['points'])
            day += timedelta(days=1)
        paired = [p for p in all_points if p['error_mw'] is not None]
        buckets = [{'label': label, 'count': 0} for label in ['< −2 GW', '−2 to −1', '−1 to 0', '0 to 1', '1 to 2', '≥ 2 GW']]
        for p in paired:
            error = p['error_mw']
            index = 0 if error < -2000 else 1 if error < -1000 else 2 if error < 0 else 3 if error < 1000 else 4 if error < 2000 else 5
            buckets[index]['count'] += 1
        return {
            'from': first.isoformat(), 'to': last.isoformat(), 'cutoff': cutoff.strftime('%H:%M'),
            'retrospective': True, 'metrics': metrics(all_points), 'daily': daily,
            'distribution': buckets,
            'worst_interval': max(paired, key=lambda p: abs(p['error_mw'])) if paired else None,
            'selection_policy': 'Latest publication at or before each decision date and cutoff; next-day targets only.',
        }
