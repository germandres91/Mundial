"""Tests del proveedor mock y la fábrica de proveedores."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.match import MatchStatus
from app.providers import get_provider
from app.providers.base import ProviderMatch
from app.providers.espn_provider import ESPNProvider
from app.providers.mock_provider import MockProvider


def test_factory_returns_mock():
    provider = get_provider("mock")
    assert provider.name == "mock"


def test_factory_returns_espn():
    provider = get_provider("espn")
    assert provider.name == "espn"


def _espn_event(state: str, name: str, home_score, away_score, clock=None) -> dict:
    return {
        "id": "760415",
        "date": "2026-06-11T19:00Z",
        "status": {"type": {"state": state, "name": name}, "displayClock": clock},
        "competitions": [
            {
                "competitors": [
                    {
                        "homeAway": "home",
                        "team": {"displayName": "Mexico"},
                        "score": home_score,
                    },
                    {
                        "homeAway": "away",
                        "team": {"displayName": "South Africa"},
                        "score": away_score,
                    },
                ]
            }
        ],
    }


def test_espn_parse_finished_match():
    pm = ESPNProvider._parse(_espn_event("post", "STATUS_FULL_TIME", "2", "0"))
    assert pm.fifa_id == "760415"
    assert pm.local == "Mexico"
    assert pm.visitante == "South Africa"
    assert pm.goles_local == 2
    assert pm.goles_visitante == 0
    assert pm.estado == MatchStatus.FINISHED


def test_espn_parse_in_progress_match():
    pm = ESPNProvider._parse(_espn_event("in", "STATUS_IN_PROGRESS", "1", "0", clock="67'"))
    assert pm.estado == MatchStatus.LIVE
    assert pm.goles_local == 1
    assert pm.goles_visitante == 0
    assert pm.minuto == "67'"


def test_espn_minute_only_when_live():
    """El minuto solo se expone en partidos en vivo, no en finalizados."""
    finished = ESPNProvider._parse(
        _espn_event("post", "STATUS_FULL_TIME", "2", "0", clock="90'+8'")
    )
    assert finished.minuto is None


def test_espn_scheduled_match_has_no_score():
    """Un partido no iniciado no debe traer marcador (evita 0-0 falsos)."""
    pm = ESPNProvider._parse(_espn_event("pre", "STATUS_SCHEDULED", "0", "0"))
    assert pm.estado == MatchStatus.SCHEDULED
    assert pm.goles_local is None
    assert pm.goles_visitante is None


def test_espn_unknown_status_falls_back_to_state():
    pm = ESPNProvider._parse(_espn_event("post", "STATUS_WEIRD_NEW", "3", "1"))
    assert pm.estado == MatchStatus.FINISHED


def test_factory_unknown_falls_back_to_mock():
    provider = get_provider("inexistente")
    assert isinstance(provider, MockProvider)


def test_mock_finalizes_past_matches(monkeypatch):
    provider = MockProvider(seed=1)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    provider._matches = [
        ProviderMatch(fifa_id="P", local="A", visitante="B", fecha=past),
        ProviderMatch(fifa_id="F", local="C", visitante="D", fecha=future),
    ]
    matches = provider.fetch_matches()
    by_id = {m.fifa_id: m for m in matches}
    assert by_id["P"].estado == MatchStatus.FINISHED
    assert by_id["P"].goles_local is not None
    assert by_id["F"].estado == MatchStatus.SCHEDULED


def test_fetch_live_matches_filters():
    provider = MockProvider(seed=2)
    past = datetime.now(timezone.utc) - timedelta(days=1)
    provider._matches = [ProviderMatch(fifa_id="P", local="A", visitante="B", fecha=past)]
    live = provider.fetch_live_matches()
    assert all(m.estado in (MatchStatus.LIVE, MatchStatus.FINISHED) for m in live)
