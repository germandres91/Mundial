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

    def set_password(self, user: User, new_password: str) -> User:
        """Establece una nueva contraseña para el usuario indicado."""
        user.hashed_password = hash_password(new_password)
        self.db.commit()
        return user

    def ensure_first_admin(self) -> None:
        """Crea/asegura el usuario administrador inicial de forma idempotente.

        - Si ya existe el admin configurado, garantiza que tenga rol ADMIN y esté
          activo (no lo recrea ni cambia su contraseña).
        - Si no existe, lo crea con la contraseña de entorno.
        """
        email = settings.first_admin_email.lower()
        existing = self.users.get_by_email(email)
        if existing:
            changed = False
            if existing.role != UserRole.ADMIN:
                existing.role = UserRole.ADMIN
                changed = True
            if not existing.is_active:
                existing.is_active = True
                changed = True
            if changed:
                self.db.commit()
                logger.info("Administrador asegurado (rol/activo): %s", email)
            return
        try:
            self.register(
                email=settings.first_admin_email,
                nombre=settings.first_admin_name,
                password=settings.first_admin_password,
                role=UserRole.ADMIN,
            )
            logger.info("Usuario administrador inicial creado: %s", email)
        except Exception:  # noqa: BLE001
            # Otra instancia/arranque pudo crearlo en paralelo; no es fatal.
            self.db.rollback()
            logger.exception("No se pudo crear el admin inicial (continuando)")
