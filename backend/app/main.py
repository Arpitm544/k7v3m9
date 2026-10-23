from datetime import date, time
from functools import lru_cache
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .analytics import Analytics, FIRST, LAST

DATA = Path(__file__).resolve().parents[1] / 'data'
app = FastAPI(title='Wind Desk API', version='1.0.0', description='Historical Elexon wind forecasts selected as of a day-ahead decision cutoff. Errors are forecast minus actual.')
app.add_middleware(CORSMiddleware, allow_origins=[s.strip() for s in os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if s.strip()], allow_methods=['GET'], allow_headers=['*'])


@lru_cache(maxsize=1)
def repository():
    try:
        manifest = json.loads((DATA / 'manifest.json').read_text())
        with gzip.open(DATA / 'snapshot.json.gz', 'rb') as stream:
            payload = stream.read()
        if hashlib.sha256(payload).hexdigest() != manifest['sha256']:
            raise ValueError('Snapshot checksum mismatch')
        return Analytics(json.loads(payload)), manifest
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(503, 'Historical snapshot unavailable. Run scripts/fetch_data.py and inspect server logs.') from exc


def validate_day(value):
    if not FIRST <= value <= LAST:
        raise HTTPException(422, 'Decision dates must be between 2026-01-01 and 2026-01-31 inclusive.')
    return value


def validate_cutoff(value):
    if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', value):
        raise HTTPException(422, 'Cutoff must use HH:MM in Europe/London, for example 09:00.')
    return time.fromisoformat(value)


@app.get('/api/health')
def health():
    _, manifest = repository()
    return {'status': 'ok', 'snapshot': manifest['sha256'][:12]}


@app.get('/api/metadata')
def metadata():
    engine, manifest = repository()
    quality = engine.accuracy(FIRST, LAST, time(9))['metrics']
    return {'decision_start': FIRST.isoformat(), 'decision_end': LAST.isoformat(),
            'timezone': 'Europe/London', 'default_cutoff': '09:00',
            'cutoff_assumption': '09:00 is a demonstration assumption, not an official auction deadline.',
            'resolution_note': 'WINDFOR is hourly in this snapshot. Each forecast is compared with the mean of two actual half-hours. This is an explicit alignment assumption; no half-hour forecasts are invented.',
            'metrics_note': 'Error = forecast − actual. Positive bias means wind overprediction. Accuracy is retrospective, not information available at the historical decision time.',
            'quality_at_default_cutoff': quality, 'manifest': manifest}


@app.get('/api/decision')
def decision(date: date = Query(...), cutoff: str = '09:00'):
    day = validate_day(date)
    selected_cutoff = validate_cutoff(cutoff)
    engine, _ = repository()
    return engine.decision(day, selected_cutoff)


@app.get('/api/accuracy')
def accuracy(first: date = Query(FIRST, alias='from'), last: date = Query(LAST, alias='to'), cutoff: str = '09:00'):
    validate_day(first)
    validate_day(last)
    selected_cutoff = validate_cutoff(cutoff)
    if first > last:
        raise HTTPException(422, 'The start date must be on or before the end date.')
    engine, _ = repository()
    return engine.accuracy(first, last, selected_cutoff)
