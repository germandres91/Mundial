"""Definición del proveedor abstracto de datos de fútbol."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.match import MatchStatus


@dataclass
class ProviderMatch:
    """Representación normalizada de un partido proveniente de cualquier API."""

    fifa_id: str
    local: str
    visitante: str
    fecha: datetime | None = None
    grupo: str | None = None
    fase: str | None = None
    goles_local: int | None = None
    goles_visitante: int | None = None
    goles_local_90: int | None = None
    goles_visitante_90: int | None = None
    penales_local: int | None = None
    penales_visitante: int | None = None
    ganador: str | None = None
    estado: MatchStatus = MatchStatus.SCHEDULED
    # Minuto de juego en vivo (texto, p. ej. "45'" o "90'+8'"), si el proveedor lo da.
    minuto: str | None = None


class BaseFootballProvider(ABC):
    """Contrato común para todos los proveedores de resultados."""

    name: str = "base"

    @abstractmethod
    def fetch_matches(self) -> list[ProviderMatch]:
        """Devuelve la lista completa de partidos del torneo."""
        raise NotImplementedError

    def fetch_live_matches(self) -> list[ProviderMatch]:
        """Devuelve partidos en vivo o recientemente finalizados.

        Por defecto filtra el resultado de :meth:`fetch_matches`.
        """
        matches = self.fetch_matches()
        return [m for m in matches if m.estado in (MatchStatus.LIVE, MatchStatus.FINISHED)]
