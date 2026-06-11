"""Tests de la lógica de intervalo inteligente del scheduler."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.jobs.scheduler import _decide_interval
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository


def test_interval_idle_when_no_matches(db):
    mode, seconds = _decide_interval(db)
    assert mode == "inactivo"
    assert seconds == max(60, settings.sync_interval_minutes * 60)


def test_interval_live_when_match_in_progress(db):
    MatchRepository(db).create(
        fifa_id="L-1",
        local="México",
        visitante="Sudáfrica",
        estado=MatchStatus.LIVE,
    )
    mode, seconds = _decide_interval(db)
    assert mode == "vivo"
    assert seconds == settings.sync_live_seconds


def test_interval_imminent_when_match_starts_soon(db):
    soon = datetime.now(timezone.utc) + timedelta(minutes=5)
    MatchRepository(db).create(
        fifa_id="S-1",
        local="Brasil",
        visitante="Marruecos",
        fecha=soon,
        estado=MatchStatus.SCHEDULED,
    )
    mode, seconds = _decide_interval(db)
    assert mode == "inminente"
    assert seconds == settings.sync_live_seconds


def test_interval_idle_when_match_far_away(db):
    far = datetime.now(timezone.utc) + timedelta(hours=3)
    MatchRepository(db).create(
        fifa_id="F-1",
        local="Argentina",
        visitante="Francia",
        fecha=far,
        estado=MatchStatus.SCHEDULED,
    )
    mode, _ = _decide_interval(db)
    assert mode == "inactivo"
