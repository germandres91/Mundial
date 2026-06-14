"""Esquemas para el dashboard y estadísticas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.match import MatchOut
from app.schemas.ranking import RankingRow


class DashboardSummary(BaseModel):
    proximo_partido: MatchOut | None = None
    ultimo_resultado: MatchOut | None = None
    lider: RankingRow | None = None
    partidos_jugados: int
    partidos_pendientes: int
    total_partidos: int
    total_participantes: int
    total_predicciones: int


class ChartPoint(BaseModel):
    label: str
    value: float


class ParticipantStats(BaseModel):
    participant_id: int
    nombre: str
    puntos_totales: int
    aciertos_exactos: int
    partidos_acertados: int
    puntos_por_fase: list[ChartPoint]


class RaceMatch(BaseModel):
    """Un partido jugado, en orden cronológico, para el eje X de la carrera."""

    orden: int
    match_id: int
    etiqueta: str
    fase: str
    fecha: datetime | None = None


class RaceSeries(BaseModel):
    """Puntaje acumulado de un participante a lo largo de los partidos."""

    participant_id: int
    nombre: str
    puntos: list[int]


class RaceResponse(BaseModel):
    """Datos de la gráfica 'Carrera al mundial'."""

    partidos: list[RaceMatch]
    series: list[RaceSeries]
