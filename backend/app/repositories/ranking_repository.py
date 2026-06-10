"""Repositorio de rankings."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ranking import Ranking


class RankingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Ranking]:
        return list(
            self.db.scalars(
                select(Ranking).order_by(Ranking.posicion.asc(), Ranking.puntos_totales.desc())
            )
        )

    def get(self, participant_id: int) -> Ranking | None:
        return self.db.get(Ranking, participant_id)

    def leader(self) -> Ranking | None:
        return self.db.scalar(
            select(Ranking).order_by(Ranking.puntos_totales.desc()).limit(1)
        )

    def upsert(
        self,
        participant_id: int,
        puntos_totales: int,
        posicion: int,
        aciertos_exactos: int,
        partidos_acertados: int,
    ) -> Ranking:
        ranking = self.get(participant_id)
        if ranking is None:
            ranking = Ranking(participant_id=participant_id)
            self.db.add(ranking)
        ranking.puntos_totales = puntos_totales
        ranking.posicion = posicion
        ranking.aciertos_exactos = aciertos_exactos
        ranking.partidos_acertados = partidos_acertados
        self.db.flush()
        return ranking
