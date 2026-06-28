"""Esquemas para predicciones de eliminatorias."""
from __future__ import annotations

from pydantic import BaseModel, Field


class RoundPredictionSubmit(BaseModel):
    match_id: int
    pred_local: int = Field(ge=0, le=99)
    pred_visitante: int = Field(ge=0, le=99)


class LatePredictionReview(BaseModel):
    note: str | None = None
