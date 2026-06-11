"""Servicio de cálculo de ranking agregado."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.ranking_repository import RankingRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.ranking import RankingRow
from app.services.scoring_service import ScoringService

logger = get_logger(__name__)


class RankingService:
    """Agrega puntajes por participante y genera el ranking ordenado."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.scores = ScoreRepository(db)
        self.rankings = RankingRepository(db)
        self.participants = ParticipantRepository(db)

    def _position_points(self) -> dict[int, int]:
        """Bonus de posiciones por participante (solo contra resultados reales)."""
        return ScoringService(self.db).position_points_by_participant()

    def recalculate(self) -> list[RankingRow]:
        """Recalcula y persiste el ranking de todos los participantes.

        El total combina los puntos de partidos y el bonus de posiciones
        finales (1° a 4°).
        """
        participants = self.participants.list()
        all_scores = self.scores.list()
        pos_points = self._position_points()

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

        def total_for(pid: int) -> int:
            return agg[pid]["puntos"] + pos_points.get(pid, 0)

        ordered = sorted(
            participants,
            key=lambda p: (total_for(p.id), agg[p.id]["exactos"]),
            reverse=True,
        )

        rows: list[RankingRow] = []
        for index, participant in enumerate(ordered, start=1):
            data = agg[participant.id]
            bonus = pos_points.get(participant.id, 0)
            total = data["puntos"] + bonus
            self.rankings.upsert(
                participant_id=participant.id,
                puntos_totales=total,
                posicion=index,
                aciertos_exactos=data["exactos"],
                partidos_acertados=data["acertados"],
            )
            rows.append(
                RankingRow(
                    participant_id=participant.id,
                    nombre=participant.nombre,
                    puntos_totales=total,
                    posicion=index,
                    aciertos_exactos=data["exactos"],
                    partidos_acertados=data["acertados"],
                    puntos_posiciones=bonus,
                )
            )
        self.db.commit()
        logger.info("Ranking recalculado para %d participantes", len(rows))
        return rows

    def get_ranking(self) -> list[RankingRow]:
        """Devuelve el ranking actual desde la base de datos."""
        pos_points = self._position_points()
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
                    puntos_posiciones=pos_points.get(ranking.participant_id, 0),
                )
            )
        return rows
