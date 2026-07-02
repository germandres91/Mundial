"""Proveedor basado en la API pública (no oficial) de ESPN."""
from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.providers.base import BaseFootballProvider, ProviderMatch
from app.utils.match_scores import (
    penalties_from_linescores,
    regulation_from_linescores,
    winner_team_name,
)

logger = get_logger(__name__)

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
    "STATUS_FINAL_AET": MatchStatus.FINISHED,
    "STATUS_FINAL_PEN": MatchStatus.FINISHED,
    "STATUS_POSTPONED": MatchStatus.POSTPONED,
    "STATUS_SUSPENDED": MatchStatus.POSTPONED,
    "STATUS_CANCELED": MatchStatus.CANCELLED,
    "STATUS_CANCELLED": MatchStatus.CANCELLED,
    "STATUS_ABANDONED": MatchStatus.CANCELLED,
    "STATUS_FORFEIT": MatchStatus.CANCELLED,
}

_STATUS_STATE_MAP = {
    "pre": MatchStatus.SCHEDULED,
    "in": MatchStatus.LIVE,
    "post": MatchStatus.FINISHED,
}

# Estados donde el marcador de la API es final (incluye TE/penales) y hay que
# consultar el summary para obtener los 90 minutos reglamentarios.
_NEEDS_REGULATION_LOOKUP = frozenset(
    {
        "STATUS_FINAL_AET",
        "STATUS_FINAL_PEN",
        "STATUS_EXTRA_TIME",
        "STATUS_SHOOTOUT",
    }
)


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
                status_name = (event.get("status") or {}).get("type", {}).get("name", "")
                if status_name in _NEEDS_REGULATION_LOOKUP or (
                    match.estado == MatchStatus.FINISHED
                    and match.goles_local is not None
                    and match.goles_local_90 is None
                ):
                    self._enrich_regulation(match, str(event.get("id")))
                parsed.append(match)
        return parsed

    def _enrich_regulation(self, match: ProviderMatch, event_id: str) -> None:
        """Completa marcador de 90', penales y ganador desde el summary de ESPN."""
        if not event_id:
            return
        try:
            resp = httpx.get(
                f"{self.BASE_URL}/{self.league}/summary",
                params={"event": event_id},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("ESPN summary %s: %s", event_id, exc)
            return

        comps = (resp.json().get("header") or {}).get("competitions") or []
        if not comps:
            return
        competitors = comps[0].get("competitors") or []
        home = next((c for c in competitors if c.get("homeAway") == "home"), None)
        away = next((c for c in competitors if c.get("homeAway") == "away"), None)
        if home is None or away is None:
            return

        gl90, gv90 = regulation_from_linescores(
            home.get("linescores"), away.get("linescores")
        )
        if gl90 is not None and gv90 is not None:
            match.goles_local_90 = gl90
            match.goles_visitante_90 = gv90

        pl, pv = penalties_from_linescores(home.get("linescores"), away.get("linescores"))
        if pl is not None and pv is not None:
            match.penales_local = pl
            match.penales_visitante = pv

        winner = winner_team_name(home, away)
        if winner:
            match.ganador = winner

    @staticmethod
    def _resolve_status(status_type: dict) -> MatchStatus:
        name = (status_type.get("name") or "").upper()
        if name in _STATUS_NAME_MAP:
            return _STATUS_NAME_MAP[name]
        state = (status_type.get("state") or "").lower()
        return _STATUS_STATE_MAP.get(state, MatchStatus.SCHEDULED)

    @staticmethod
    def _parse_score(value: object, started: bool) -> int | None:
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

        status = event.get("status") or {}
        status_type = status.get("type") or {}
        status_name = (status_type.get("name") or "").upper()
        estado = cls._resolve_status(status_type)
        started = estado in (MatchStatus.LIVE, MatchStatus.FINISHED)

        minuto = None
        if estado == MatchStatus.LIVE:
            clock = status.get("displayClock") or status.get("clock")
            if clock:
                minuto = str(clock).strip()

        utc = event.get("date")
        fecha = None
        if utc:
            try:
                fecha = datetime.fromisoformat(utc.replace("Z", "+00:00"))
            except ValueError:
                fecha = None

        gl_final = cls._parse_score(home.get("score"), started)
        gv_final = cls._parse_score(away.get("score"), started)

        # Marcador reglamentario disponible en el scoreboard (raro).
        gl90, gv90 = regulation_from_linescores(
            home.get("linescores"), away.get("linescores")
        )
        if gl90 is None and status_name == "STATUS_FULL_TIME" and gl_final is not None:
            gl90, gv90 = gl_final, gv_final

        pl, pv = penalties_from_linescores(home.get("linescores"), away.get("linescores"))
        ganador = winner_team_name(home, away) if estado == MatchStatus.FINISHED else None

        return ProviderMatch(
            fifa_id=str(event.get("id")),
            local=(home.get("team") or {}).get("displayName", "?"),
            visitante=(away.get("team") or {}).get("displayName", "?"),
            fecha=fecha,
            grupo=None,
            fase=None,
            goles_local=gl_final,
            goles_visitante=gv_final,
            goles_local_90=gl90,
            goles_visitante_90=gv90,
            penales_local=pl,
            penales_visitante=pv,
            ganador=ganador,
            estado=estado,
            minuto=minuto,
        )
