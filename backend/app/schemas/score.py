"""Esquemas de puntajes."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    participant_id: int
    match_id: int
    puntos: int
    detalle: str | None = None
