"""Proveedor basado en football-data.org (https://www.football-data.org)."""
from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.providers.base import BaseFootballProvider, ProviderMatch

logger = get_logger(__name__)

_STATUS_MAP = {
    "SCHEDULED": MatchStatus.SCHEDULED,
    "TIMED": MatchStatus.SCHEDULED,
    "IN_PLAY": MatchStatus.LIVE,
    "PAUSED": MatchStatus.LIVE,
    "FINISHED": MatchStatus.FINISHED,
    "POSTPONED": MatchStatus.POSTPONED,
    "SUSPENDED": MatchStatus.POSTPONED,
    "CANCELLED": MatchStatus.CANCELLED,
}


class FootballDataProvider(BaseFootballProvider):
    """Consume la API de football-data.org para una competición (por defecto WC)."""

    name = "football_data"
    BASE_URL = "https://api.football-data.org/v4"

    def __init__(self, api_key: str | None = None, competition: str | None = None) -> None:
        self.api_key = api_key or settings.football_api_key
        self.competition = competition or settings.football_competition_id
        self.timeout = settings.football_api_timeout

    def _headers(self) -> dict[str, str]:
        return {"X-Auth-Token": self.api_key}

    def fetch_matches(self) -> list[ProviderMatch]:
        url = f"{self.BASE_URL}/competitions/{self.competition}/matches"
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=self.timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Error consultando football-data.org: %s", exc)
            return []
        return [self._parse(m) for m in resp.json().get("matches", [])]

    @staticmethod
    def _parse(item: dict) -> ProviderMatch:
        score = item.get("score", {}).get("fullTime", {})
        utc = item.get("utcDate")
        return ProviderMatch(
            fifa_id=str(item.get("id")),
            local=item.get("homeTeam", {}).get("name", "?"),
            visitante=item.get("awayTeam", {}).get("name", "?"),
            fecha=datetime.fromisoformat(utc.replace("Z", "+00:00")) if utc else None,
            grupo=item.get("group"),
            fase=item.get("stage"),
            goles_local=score.get("home"),
            goles_visitante=score.get("away"),
            estado=_STATUS_MAP.get(item.get("status", ""), MatchStatus.SCHEDULED),
        )
