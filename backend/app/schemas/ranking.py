"""Esquemas de ranking."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class RankingRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    participant_id: int
    nombre: str
    puntos_totales: int
    posicion: int
    aciertos_exactos: int
    partidos_acertados: int
