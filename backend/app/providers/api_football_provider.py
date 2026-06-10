"""Proveedor basado en API-FOOTBALL (api-sports.io)."""
from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.providers.base import BaseFootballProvider, ProviderMatch

logger = get_logger(__name__)

_FINISHED = {"FT", "AET", "PEN"}
_LIVE = {"1H", "2H", "HT", "ET", "P", "LIVE"}


class APIFootballProvider(BaseFootballProvider):
    """Consume la API de API-FOOTBALL (v3) para la Copa del Mundo."""

    name = "api_football"
    BASE_URL = "https://v3.football.api-sports.io"

    def __init__(self, api_key: str | None = None, league: str = "1", season: str = "2026") -> None:
        self.api_key = api_key or settings.football_api_key
        self.league = league
        self.season = season
        self.timeout = settings.football_api_timeout

    def _headers(self) -> dict[str, str]:
        return {"x-apisports-key": self.api_key}

    def fetch_matches(self) -> list[ProviderMatch]:
        url = f"{self.BASE_URL}/fixtures"
        params = {"league": self.league, "season": self.season}
        try:
            resp = httpx.get(url, headers=self._headers(), params=params, timeout=self.timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Error consultando API-FOOTBALL: %s", exc)
            return []
        return [self._parse(m) for m in resp.json().get("response", [])]

    @staticmethod
    def _map_status(short: str) -> MatchStatus:
        if short in _FINISHED:
            return MatchStatus.FINISHED
        if short in _LIVE:
            return MatchStatus.LIVE
        if short in {"PST"}:
            return MatchStatus.POSTPONED
        if short in {"CANC", "ABD"}:
            return MatchStatus.CANCELLED
        return MatchStatus.SCHEDULED

    @classmethod
    def _parse(cls, item: dict) -> ProviderMatch:
        fixture = item.get("fixture", {})
        teams = item.get("teams", {})
        goals = item.get("goals", {})
        league = item.get("league", {})
        ts = fixture.get("date")
        return ProviderMatch(
            fifa_id=str(fixture.get("id")),
            local=teams.get("home", {}).get("name", "?"),
            visitante=teams.get("away", {}).get("name", "?"),
            fecha=datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None,
            grupo=league.get("round"),
            fase=league.get("round"),
            goles_local=goals.get("home"),
            goles_visitante=goals.get("away"),
            estado=cls._map_status(fixture.get("status", {}).get("short", "")),
        )
