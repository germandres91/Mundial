"""Esquemas de autenticación y usuarios."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserCreate(BaseModel):
    email: EmailStr
    nombre: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.PARTICIPANT


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nombre: str
    role: UserRole
    is_active: bool
    participant_id: int | None = None
