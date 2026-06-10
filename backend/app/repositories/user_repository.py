"""Repositorio de usuarios."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def list(self) -> list[User]:
        return list(self.db.scalars(select(User).order_by(User.email)))

    def create(
        self,
        email: str,
        nombre: str,
        hashed_password: str,
        role: UserRole = UserRole.PARTICIPANT,
        participant_id: int | None = None,
    ) -> User:
        user = User(
            email=email,
            nombre=nombre,
            hashed_password=hashed_password,
            role=role,
            participant_id=participant_id,
        )
        self.db.add(user)
        self.db.flush()
        return user
