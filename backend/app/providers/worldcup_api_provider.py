"""Proveedor genérico para una API REST de Mundial con esquema simple.

Pensado para integrarse con servicios tipo "worldcup json api" que devuelven
una lista de partidos con campos directos. Ajusta el mapeo según tu API.
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.providers.base import BaseFootballProvider, ProviderMatch

logger = get_logger(__name__)


class WorldCupAPIProvider(BaseFootballProvider):
    """Consume una API REST configurable mediante FOOTBALL_API_KEY como URL base."""

    name = "worldcup_api"

    def __init__(self, base_url: str | None = None) -> None:
        # Para este proveedor reutilizamos la API key como URL base del servicio.
        self.base_url = (base_url or settings.football_api_key or "").rstrip("/")
        self.timeout = settings.football_api_timeout

    def fetch_matches(self) -> list[ProviderMatch]:
        if not self.base_url:
            logger.warning("WorldCupAPIProvider sin URL base configurada (FOOTBALL_API_KEY)")
            return []
        url = f"{self.base_url}/matches"
        try:
            resp = httpx.get(url, timeout=self.timeout)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Error consultando WorldCup API: %s", exc)
            return []
        data = resp.json()
        items = data if isinstance(data, list) else data.get("matches", [])
        return [self._parse(m) for m in items]

    @staticmethod
    def _parse(item: dict) -> ProviderMatch:
        fecha = item.get("datetime") or item.get("fecha")
        status = (item.get("status") or "").lower()
        estado = MatchStatus.SCHEDULED
        if status in {"completed", "finished"}:
            estado = MatchStatus.FINISHED
        elif status in {"in progress", "live"}:
            estado = MatchStatus.LIVE
        return ProviderMatch(
            fifa_id=str(item.get("fifa_id") or item.get("id")),
            local=item.get("home_team", item.get("local", "?")),
            visitante=item.get("away_team", item.get("visitante", "?")),
            fecha=datetime.fromisoformat(fecha.replace("Z", "+00:00")) if fecha else None,
            grupo=item.get("group") or item.get("grupo"),
            fase=item.get("stage") or item.get("fase"),
            goles_local=item.get("home_score", item.get("goles_local")),
            goles_visitante=item.get("away_score", item.get("goles_visitante")),
            estado=estado,
        )
