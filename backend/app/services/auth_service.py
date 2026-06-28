"""Servicio de autenticación de usuarios."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.config import resolve_path, settings
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
        normalized = email.strip().lower()
        if self.users.get_by_email(normalized):
            raise ValueError(f"El email ya está registrado: {normalized}")
        user = self.users.create(
            email=normalized,
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

    def ensure_seed_users(self) -> int:
        """Crea usuarios de acceso predefinidos desde data/users_seed.json.

        Es idempotente: omite los que ya existen (por email) y no toca sus
        contraseñas. Los usuarios se crean con rol PARTICIPANT (solo lectura).
        Devuelve cuántos usuarios nuevos se crearon.
        """
        path = resolve_path("data/users_seed.json")
        if not path.exists():
            return 0
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo leer users_seed.json")
            return 0

        created = 0
        for item in payload.get("usuarios", []):
            email = str(item.get("email", "")).strip().lower()
            password = str(item.get("password", "")).strip()
            nombre = str(item.get("nombre", "")).strip() or email.split("@")[0]
            if not email or not password:
                continue
            if self.users.get_by_email(email):
                continue
            try:
                self.register(
                    email=email,
                    nombre=nombre,
                    password=password,
                    role=UserRole.PARTICIPANT,
                )
                created += 1
            except ValueError:
                self.db.rollback()
            except Exception:  # noqa: BLE001
                self.db.rollback()
                logger.exception("No se pudo crear el usuario semilla: %s", email)
        if created:
            logger.info("Usuarios semilla creados: %d", created)
        return created

    def ensure_first_admin(self, *, sync_password: bool | None = None) -> None:
        """Crea/asegura el usuario administrador inicial de forma idempotente.

        - Si ya existe el admin configurado, garantiza rol ADMIN y activo.
        - Con ``sync_password=True`` (o ``admin_sync_password_on_boot``), restablece
          la contraseña desde ``FIRST_ADMIN_PASSWORD`` sin tocar otros usuarios.
        - Si no existe, lo crea con la contraseña de entorno.
        """
        if sync_password is None:
            sync_password = settings.admin_sync_password_on_boot
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
            if sync_password and settings.first_admin_password:
                existing.hashed_password = hash_password(settings.first_admin_password)
                changed = True
            if changed:
                self.db.commit()
                logger.info("Administrador asegurado: %s (sync_password=%s)", email, sync_password)
            return
        try:
            self.register(
                email=settings.first_admin_email,
                nombre=settings.first_admin_name,
                password=settings.first_admin_password,
                role=UserRole.ADMIN,
            )
            logger.info("Usuario administrador inicial creado: %s", email)
        except ValueError:
            # Condición de carrera: otro worker lo creó entre la consulta y el insert.
            self.db.rollback()
            logger.info("Admin ya existía al crear (carrera concurrente): %s", email)
        except Exception:  # noqa: BLE001
            self.db.rollback()
            # Reintenta leer por si el insert falló por UNIQUE pero el registro quedó.
            if self.users.get_by_email(email):
                logger.info("Admin recuperado tras error de creación: %s", email)
            else:
                logger.exception("No se pudo crear el admin inicial (continuando)")

    def _resolve_participant_for_user(self, user: User):
        from app.repositories.participant_repository import ParticipantRepository

        participants = ParticipantRepository(self.db)
        part = participants.get_by_email(user.email.lower())
        if part is None:
            part = participants.find_by_nombre(user.nombre)
        if part is None and user.email.lower() == settings.first_admin_email.lower():
            part = participants.find_by_nombre(settings.first_admin_name)
        return part

    def link_user_to_participant(self, user: User) -> bool:
        """Vincula un usuario con su participante (email o nombre). Devuelve si hubo cambio."""
        if user.participant_id is not None:
            return False
        part = self._resolve_participant_for_user(user)
        if part is None:
            return False
        user.participant_id = part.id
        self.db.commit()
        logger.info("Usuario %s vinculado al participante %s", user.email, part.nombre)
        return True

    def link_users_to_participants(self) -> int:
        """Vincula cuentas de acceso con participantes por email o nombre (idempotente)."""
        linked = 0
        for user in self.users.list():
            if user.participant_id is not None:
                continue
            part = self._resolve_participant_for_user(user)
            if part is None:
                continue
            user.participant_id = part.id
            linked += 1
        if linked:
            self.db.commit()
            logger.info("Usuarios vinculados a participantes: %d", linked)
        return linked
