"""Repositorio de puntajes."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.score import Score


class ScoreRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, participant_id: int | None = None) -> list[Score]:
        stmt = select(Score)
        if participant_id:
            stmt = stmt.where(Score.participant_id == participant_id)
        return list(self.db.scalars(stmt))

    def get_for(self, participant_id: int, match_id: int) -> Score | None:
        return self.db.scalar(
            select(Score).where(
                Score.participant_id == participant_id, Score.match_id == match_id
            )
        )

    def upsert(
        self, participant_id: int, match_id: int, puntos: int, detalle: str | None
    ) -> Score:
        existing = self.get_for(participant_id, match_id)
        if existing:
            existing.puntos = puntos
            existing.detalle = detalle
            self.db.flush()
            return existing
        score = Score(
            participant_id=participant_id,
            match_id=match_id,
            puntos=puntos,
            detalle=detalle,
        )
        self.db.add(score)
        self.db.flush()
        return score
