"""Esquemas de predicciones."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.match import MatchOut


class PredictionBase(BaseModel):
    participant_id: int
    match_id: int
    pred_local: int = Field(ge=0, le=99)
    pred_visitante: int = Field(ge=0, le=99)


class PredictionCreate(PredictionBase):
    pass


class PredictionUpdate(BaseModel):
    pred_local: int = Field(ge=0, le=99)
    pred_visitante: int = Field(ge=0, le=99)


class PredictionOut(PredictionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    locked_at: datetime | None = None
    created_at: datetime


class PredictionWithMatch(PredictionOut):
    match: MatchOut
