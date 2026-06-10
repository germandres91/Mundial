"""Esquemas de participantes."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ParticipantBase(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    email: EmailStr


class ParticipantCreate(ParticipantBase):
    pass


class ParticipantUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None


class ParticipantOut(ParticipantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fecha_creacion: datetime
