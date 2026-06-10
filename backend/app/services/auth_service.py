"""Servicio de autenticación de usuarios."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def authenticate(self, email: str, password: str) -> User | None:
        user = self.users.get_by_email(email.lower())
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def login(self, email: str, password: str) -> str | None:
        user = self.authenticate(email, password)
        if user is None:
            return None
        return create_access_token(user.id, extra={"role": user.role.value})

    def register(
        self,
        email: str,
        nombre: str,
        password: str,
        role: UserRole = UserRole.PARTICIPANT,
        participant_id: int | None = None,
    ) -> User:
        user = self.users.create(
            email=email.lower(),
            nombre=nombre,
            hashed_password=hash_password(password),
            role=role,
            participant_id=participant_id,
        )
        self.db.commit()
        return user

    def ensure_first_admin(self) -> None:
        """Crea el usuario administrador inicial si no existe ninguno."""
        existing = self.users.get_by_email(settings.first_admin_email.lower())
        if existing:
            return
        self.register(
            email=settings.first_admin_email,
            nombre=settings.first_admin_name,
            password=settings.first_admin_password,
            role=UserRole.ADMIN,
        )
        logger.info("Usuario administrador inicial creado: %s", settings.first_admin_email)
