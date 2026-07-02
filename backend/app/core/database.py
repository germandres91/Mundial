"""Configuración del motor de base de datos y sesiones SQLAlchemy."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import resolved_database_url, settings
from app.core.logging import get_logger

logger = get_logger(__name__)


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


# Columnas agregadas después del primer despliegue. Como el arranque usa
# create_all (que no altera tablas existentes), las añadimos aquí de forma
# idempotente para no perder datos ni requerir migraciones manuales.
_COLUMN_UPGRADES: dict[str, dict[str, str]] = {
    "matches": {
        "minuto": "VARCHAR(16)",
        "goles_local_90": "INTEGER",
        "goles_visitante_90": "INTEGER",
        "penales_local": "INTEGER",
        "penales_visitante": "INTEGER",
        "ganador": "VARCHAR(80)",
    },
    "predictions": {"locked_at": "TIMESTAMP WITH TIME ZONE"},
}


def _ensure_columns() -> None:
    """Agrega columnas faltantes a tablas existentes (SQLite y PostgreSQL)."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    for table, columns in _COLUMN_UPGRADES.items():
        if table not in existing_tables:
            continue
        present = {col["name"] for col in inspector.get_columns(table)}
        for name, ddl in columns.items():
            if name in present:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {ddl}'))
                logger.info("Columna añadida: %s.%s", table, name)
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo añadir la columna %s.%s", table, name)


def init_db() -> None:
    """Crea todas las tablas declaradas (uso en desarrollo / arranque)."""
    # Importa los modelos para registrarlos en el metadata
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()
