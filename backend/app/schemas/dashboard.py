"""Esquemas para el dashboard y estadísticas."""
from __future__ import annotations

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
