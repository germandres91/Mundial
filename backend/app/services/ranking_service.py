"""Servicio de cálculo de ranking agregado."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.ranking_repository import RankingRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.ranking import RankingRow

logger = get_logger(__name__)


class RankingService:
    """Agrega puntajes por participante y genera el ranking ordenado."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.scores = ScoreRepository(db)
        self.rankings = RankingRepository(db)
        self.participants = ParticipantRepository(db)

    def recalculate(self) -> list[RankingRow]:
        """Recalcula y persiste el ranking de todos los participantes."""
        participants = self.participants.list()
        all_scores = self.scores.list()

        agg: dict[int, dict[str, int]] = {
            p.id: {"puntos": 0, "exactos": 0, "acertados": 0} for p in participants
        }
        for score in all_scores:
            bucket = agg.setdefault(
                score.participant_id, {"puntos": 0, "exactos": 0, "acertados": 0}
            )
            bucket["puntos"] += score.puntos
            if score.detalle == "Marcador exacto":
                bucket["exactos"] += 1
            if score.puntos > 0:
                bucket["acertados"] += 1

        ordered = sorted(
            participants,
            key=lambda p: (agg[p.id]["puntos"], agg[p.id]["exactos"]),
            reverse=True,
        )

        rows: list[RankingRow] = []
        for index, participant in enumerate(ordered, start=1):
            data = agg[participant.id]
            self.rankings.upsert(
                participant_id=participant.id,
                puntos_totales=data["puntos"],
                posicion=index,
                aciertos_exactos=data["exactos"],
                partidos_acertados=data["acertados"],
            )
            rows.append(
                RankingRow(
                    participant_id=participant.id,
                    nombre=participant.nombre,
                    puntos_totales=data["puntos"],
                    posicion=index,
                    aciertos_exactos=data["exactos"],
                    partidos_acertados=data["acertados"],
                )
            )
        self.db.commit()
        logger.info("Ranking recalculado para %d participantes", len(rows))
        return rows

    def get_ranking(self) -> list[RankingRow]:
        """Devuelve el ranking actual desde la base de datos."""
        rows: list[RankingRow] = []
        for ranking in self.rankings.list():
            nombre = ranking.participant.nombre if ranking.participant else "?"
            rows.append(
                RankingRow(
                    participant_id=ranking.participant_id,
                    nombre=nombre,
                    puntos_totales=ranking.puntos_totales,
                    posicion=ranking.posicion,
                    aciertos_exactos=ranking.aciertos_exactos,
                    partidos_acertados=ranking.partidos_acertados,
                )
            )
        return rows
