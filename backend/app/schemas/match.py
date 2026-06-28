"""Esquemas de partidos."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.match import MatchStatus
from app.utils.datetime_fmt import utc_iso


class MatchBase(BaseModel):
    fifa_id: str | None = None
    grupo: str | None = None
    fase: str | None = None
    local: str = Field(min_length=1, max_length=80)
    visitante: str = Field(min_length=1, max_length=80)
    fecha: datetime | None = None


class MatchCreate(MatchBase):
    pass


class MatchUpdate(BaseModel):
    grupo: str | None = None
    fase: str | None = None
    fecha: datetime | None = None
    goles_local: int | None = Field(default=None, ge=0)
    goles_visitante: int | None = Field(default=None, ge=0)
    estado: MatchStatus | None = None


class MatchResult(BaseModel):
    goles_local: int = Field(ge=0)
    goles_visitante: int = Field(ge=0)
    estado: MatchStatus = MatchStatus.FINISHED


class MatchOut(MatchBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    goles_local: int | None = None
    goles_visitante: int | None = None
    estado: MatchStatus
    minuto: str | None = None

    @field_serializer("fecha")
    def _serialize_fecha(self, value: datetime | None) -> str | None:
        return utc_iso(value)
