"""Repositorio de partidos."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.match import Match, MatchStatus


class MatchRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, fase: str | None = None, estado: MatchStatus | None = None) -> list[Match]:
        stmt = select(Match).order_by(Match.fecha.asc().nullslast(), Match.id)
        if fase:
            stmt = stmt.where(Match.fase == fase)
        if estado:
            stmt = stmt.where(Match.estado == estado)
        return list(self.db.scalars(stmt))

    def get(self, match_id: int) -> Match | None:
        return self.db.get(Match, match_id)

    def get_by_fifa_id(self, fifa_id: str) -> Match | None:
        return self.db.scalar(select(Match).where(Match.fifa_id == fifa_id))

    def create(self, **kwargs) -> Match:
        match = Match(**kwargs)
        self.db.add(match)
        self.db.flush()
        return match

    def count(self, estado: MatchStatus | None = None) -> int:
        stmt = select(func.count()).select_from(Match)
        if estado:
            stmt = stmt.where(Match.estado == estado)
        return int(self.db.scalar(stmt) or 0)

    def next_match(self) -> Match | None:
        now = datetime.now(timezone.utc)
        stmt = (
            select(Match)
            .where(Match.estado == MatchStatus.SCHEDULED)
            .where(Match.fecha.is_not(None))
            .where(Match.fecha >= now)
            .order_by(Match.fecha.asc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def last_finished(self) -> Match | None:
        stmt = (
            select(Match)
            .where(Match.estado == MatchStatus.FINISHED)
            .order_by(Match.fecha.desc().nullslast(), Match.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def finished_matches(self) -> list[Match]:
        return list(
            self.db.scalars(select(Match).where(Match.estado == MatchStatus.FINISHED))
        )
