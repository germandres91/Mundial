"""Repositorio de auditoría."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def log(
        self,
        accion: str,
        actor: str | None = None,
        entidad: str | None = None,
        detalle: str | None = None,
    ) -> AuditLog:
        entry = AuditLog(accion=accion, actor=actor, entidad=entidad, detalle=detalle)
        self.db.add(entry)
        self.db.flush()
        return entry

    def list(self, limit: int = 200) -> list[AuditLog]:
        return list(
            self.db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
        )

    def last_by_accion(self, accion: str) -> AuditLog | None:
        return self.db.scalar(
            select(AuditLog)
            .where(AuditLog.accion == accion)
            .order_by(AuditLog.created_at.desc())
            .limit(1)
        )
