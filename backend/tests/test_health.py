"""SCRUM-220 — /api/health tells the truth about the database.

The pilot's Route53 canary (bridgeway-portal/ops/uptime.tf) alarms on any
non-2xx from this endpoint; a hardcoded 200 hid DB-down outages while every
real endpoint 500ed. Recorded decision: mirror the portal's SCRUM-151 shape —
SELECT 1 behind a 2s timeout, 503 on failure.
"""
from contextlib import asynccontextmanager

import pytest

from app import main as app_main


async def test_health_ok_when_db_answers(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_health_503_when_db_unreachable(client, monkeypatch):
    @asynccontextmanager
    async def _dead_connect():
        raise ConnectionRefusedError("db down")
        yield  # pragma: no cover

    class _DeadEngine:
        def connect(self):
            return _dead_connect()

    monkeypatch.setattr(app_main, "engine", _DeadEngine())
    r = await client.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"status": "db_unreachable"}