"""Endpoints de autenticación."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, Token, UserOut
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> Token:
    """Inicia sesión con email y contraseña (JSON)."""
    token = AuthService(db).login(payload.email, payload.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )
    return Token(access_token=token)


@router.post("/token", response_model=Token, include_in_schema=False)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> Token:
    """Compatibilidad OAuth2 (form-urlencoded) para la documentación Swagger."""
    token = AuthService(db).login(form.username, form.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas"
        )
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(db: Session = Depends(get_db), current: User = Depends(get_current_user)) -> User:
    """Devuelve los datos del usuario autenticado."""
    if current.participant_id is None:
        AuthService(db).link_user_to_participant(current)
        db.refresh(current)
    return current
