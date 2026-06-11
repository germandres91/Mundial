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
        if not self.api_key:
            logger.error(
                "football-data.org sin API key: define FOOTBALL_API_KEY en el entorno"
            )
            return []
        url = f"{self.BASE_URL}/competitions/{self.competition}/matches"
        try:
            resp = httpx.get(url, headers=self._headers(), timeout=self.timeout)
            if resp.status_code == 429:
                logger.warning(
                    "football-data.org: límite de peticiones alcanzado (429). "
                    "Aumenta SYNC_INTERVAL_MINUTES."
                )
                return []
            if resp.status_code in (401, 403):
                logger.error(
                    "football-data.org: token inválido o sin acceso a '%s' (%s)",
                    self.competition,
                    resp.status_code,
                )
                return []
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Error consultando football-data.org: %s", exc)
            return []
        matches = resp.json().get("matches", [])
        logger.info("football-data.org devolvió %d partidos (%s)", len(matches), self.competition)
        return [self._parse(m) for m in matches]

    @staticmethod
    def _parse_group(raw: str | None) -> str | None:
        if not raw:
            return None
        if raw.startswith("GROUP_"):
            return raw.replace("GROUP_", "")
        return raw

    @staticmethod
    def _parse(item: dict) -> ProviderMatch:
        score = item.get("score", {}).get("fullTime", {})
        utc = item.get("utcDate")
        stage = item.get("stage") or ""
        fase = "Fase de grupos" if stage == "GROUP_STAGE" else stage.replace("_", " ").title()
        return ProviderMatch(
            fifa_id=str(item.get("id")),
            local=item.get("homeTeam", {}).get("name", "?"),
            visitante=item.get("awayTeam", {}).get("name", "?"),
            fecha=datetime.fromisoformat(utc.replace("Z", "+00:00")) if utc else None,
            grupo=FootballDataProvider._parse_group(item.get("group")),
            fase=fase,
            goles_local=score.get("home"),
            goles_visitante=score.get("away"),
            estado=_STATUS_MAP.get(item.get("status", ""), MatchStatus.SCHEDULED),
        )
