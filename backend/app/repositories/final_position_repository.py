"""Repositorio de las posiciones finales reales del torneo."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.final_position import FinalPosition


class FinalPositionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[FinalPosition]:
        return list(
            self.db.scalars(
                select(FinalPosition).order_by(FinalPosition.posicion)
            )
        )

    def as_map(self) -> dict[int, str]:
        return {fp.posicion: fp.equipo for fp in self.list()}

    def upsert(self, posicion: int, equipo: str) -> FinalPosition:
        existing = self.db.get(FinalPosition, posicion)
        if existing:
            existing.equipo = equipo
            self.db.flush()
            return existing
        fp = FinalPosition(posicion=posicion, equipo=equipo)
        self.db.add(fp)
        self.db.flush()
        return fp

    def delete(self, posicion: int) -> bool:
        existing = self.db.get(FinalPosition, posicion)
        if existing is None:
            return False
        self.db.delete(existing)
        self.db.flush()
        return True

    def clear(self) -> int:
        rows = self.list()
        for row in rows:
            self.db.delete(row)
        self.db.flush()
        return len(rows)
