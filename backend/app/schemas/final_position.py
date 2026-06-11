"""Esquemas de las posiciones finales reales del torneo."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FinalPositionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    posicion: int = Field(ge=1, le=4)
    equipo: str = ""


class FinalPositionsUpdate(BaseModel):
    posiciones: list[FinalPositionItem]
