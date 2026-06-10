"""Repositorio de reglas de puntaje."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scoring_rule import ScoringRule


class ScoringRuleRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, only_active: bool = False) -> list[ScoringRule]:
        stmt = select(ScoringRule).order_by(ScoringRule.puntos.desc())
        if only_active:
            stmt = stmt.where(ScoringRule.activo.is_(True))
        return list(self.db.scalars(stmt))

    def get_by_code(self, code: str) -> ScoringRule | None:
        return self.db.scalar(select(ScoringRule).where(ScoringRule.code == code))

    def upsert(self, code: str, descripcion: str, puntos: int, activo: bool = True) -> ScoringRule:
        rule = self.get_by_code(code)
        if rule is None:
            rule = ScoringRule(code=code)
            self.db.add(rule)
        rule.descripcion = descripcion
        rule.puntos = puntos
        rule.activo = activo
        self.db.flush()
        return rule

    def as_points_map(self) -> dict[str, int]:
        return {r.code: r.puntos for r in self.list(only_active=True)}
