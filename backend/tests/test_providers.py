"""Tests del proveedor mock y la fábrica de proveedores."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.match import MatchStatus
from app.providers import get_provider
from app.providers.base import ProviderMatch
from app.providers.mock_provider import MockProvider


def test_factory_returns_mock():
    provider = get_provider("mock")
    assert provider.name == "mock"


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
