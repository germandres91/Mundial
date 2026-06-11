"""Esquemas de partidos."""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.models.match import MatchStatus


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

    @field_serializer("fecha")
    def _serialize_fecha(self, value: datetime | None) -> str | None:
        """Devuelve la fecha siempre en UTC con offset explícito.

        En SQLite las fechas se guardan sin zona; aquí asumimos que son UTC y
        emitimos ISO-8601 con `+00:00` para que el navegador la convierta bien
        a la hora local (Colombia) sin desfases.
        """
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
