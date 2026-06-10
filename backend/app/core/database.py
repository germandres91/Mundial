"""Configuración del motor de base de datos y sesiones SQLAlchemy."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import resolved_database_url, settings


class Base(DeclarativeBase):
    """Clase base declarativa para todos los modelos ORM."""


def _build_engine():
    url = resolved_database_url(settings.database_url)
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True, future=True)


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dependencia FastAPI que entrega una sesión y la cierra al finalizar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Crea todas las tablas declaradas (uso en desarrollo / arranque)."""
    # Importa los modelos para registrarlos en el metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
