"""Esquemas de reglas de puntaje."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ScoringRuleBase(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    descripcion: str
    puntos: int = Field(ge=0)
    activo: bool = True


class ScoringRuleUpdate(BaseModel):
    descripcion: str | None = None
    puntos: int | None = Field(default=None, ge=0)
    activo: bool | None = None


class ScoringRuleOut(ScoringRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
