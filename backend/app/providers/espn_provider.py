"""Proveedor basado en la API pública (no oficial) de ESPN.

ESPN expone un scoreboard gratuito y sin API key con marcadores en tiempo real,
minuto de juego y estado del partido. Cubre el Mundial vía el slug `fifa.world`.

Endpoint:
    https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard

Notas:
- Es una API no documentada/oficial: puede cambiar sin previo aviso.
- Los nombres de selección vienen en inglés; `app.utils.teams.team_code` ya los
  normaliza para emparejarlos con el calendario en español.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.providers.base import BaseFootballProvider, ProviderMatch

logger = get_logger(__name__)

# ESPN expone el estado en `status.type.name` (preferido) y `status.type.state`.
_STATUS_NAME_MAP = {
    "STATUS_SCHEDULED": MatchStatus.SCHEDULED,
    "STATUS_DELAYED": MatchStatus.SCHEDULED,
    "STATUS_IN_PROGRESS": MatchStatus.LIVE,
    "STATUS_FIRST_HALF": MatchStatus.LIVE,
    "STATUS_SECOND_HALF": MatchStatus.LIVE,
    "STATUS_HALFTIME": MatchStatus.LIVE,
    "STATUS_END_PERIOD": MatchStatus.LIVE,
    "STATUS_EXTRA_TIME": MatchStatus.LIVE,
    "STATUS_SHOOTOUT": MatchStatus.LIVE,
    "STATUS_FULL_TIME": MatchStatus.FINISHED,
    "STATUS_FINAL": MatchStatus.FINISHED,
    "STATUS_POSTPONED": MatchStatus.POSTPONED,
    "STATUS_SUSPENDED": MatchStatus.POSTPONED,
    "STATUS_CANCELED": MatchStatus.CANCELLED,
    "STATUS_CANCELLED": MatchStatus.CANCELLED,
    "STATUS_ABANDONED": MatchStatus.CANCELLED,
    "STATUS_FORFEIT": MatchStatus.CANCELLED,
}

# Fallback por `state` cuando el `name` no está mapeado.
_STATUS_STATE_MAP = {
    "pre": MatchStatus.SCHEDULED,
    "in": MatchStatus.LIVE,
    "post": MatchStatus.FINISHED,
}


class ESPNProvider(BaseFootballProvider):
    """Consume el scoreboard de ESPN para la Copa del Mundo."""

    name = "espn"
    BASE_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer"

    def __init__(self, league: str | None = None) -> None:
        self.league = league or settings.espn_league
        self.timeout = settings.football_api_timeout
        self.date_range = settings.espn_date_range

    def _url(self) -> str:
        return f"{self.BASE_URL}/{self.league}/scoreboard"

    def fetch_matches(self) -> list[ProviderMatch]:
        params = {"limit": 500}
        if self.date_range:
            params["dates"] = self.date_range
        try:
            resp = httpx.get(self._url(), params=params, timeout=self.timeout)
            if resp.status_code == 429:
                logger.warning("ESPN: límite de peticiones alcanzado (429).")
                return []
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Error consultando ESPN: %s", exc)
            return []

        events = resp.json().get("events", [])
        logger.info("ESPN devolvió %d partidos (%s)", len(events), self.league)
        parsed: list[ProviderMatch] = []
        for event in events:
            match = self._parse(event)
            if match is not None:
                parsed.append(match)
        return parsed

    @staticmethod
    def _resolve_status(status_type: dict) -> MatchStatus:
        name = (status_type.get("name") or "").upper()
        if name in _STATUS_NAME_MAP:
            return _STATUS_NAME_MAP[name]
        state = (status_type.get("state") or "").lower()
        return _STATUS_STATE_MAP.get(state, MatchStatus.SCHEDULED)

    @staticmethod
    def _parse_score(value: object, started: bool) -> int | None:
        """Convierte el marcador a entero solo si el partido ya empezó."""
        if not started:
            return None
        try:
            return int(str(value))
        except (TypeError, ValueError):
            return None

    @classmethod
    def _parse(cls, event: dict) -> ProviderMatch | None:
        competitions = event.get("competitions") or []
        if not competitions:
            return None
        competition = competitions[0]
        competitors = competition.get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if home is None or away is None:
            return None

        status_type = (event.get("status") or {}).get("type") or {}
        estado = cls._resolve_status(status_type)
        started = estado in (MatchStatus.LIVE, MatchStatus.FINISHED)

        utc = event.get("date")
        fecha = None
        if utc:
            try:
                fecha = datetime.fromisoformat(utc.replace("Z", "+00:00"))
            except ValueError:
                fecha = None

        return ProviderMatch(
            fifa_id=str(event.get("id")),
            local=(home.get("team") or {}).get("displayName", "?"),
            visitante=(away.get("team") or {}).get("displayName", "?"),
            fecha=fecha,
            grupo=None,
            fase=None,
            goles_local=cls._parse_score(home.get("score"), started),
            goles_visitante=cls._parse_score(away.get("score"), started),
            estado=estado,
        )
