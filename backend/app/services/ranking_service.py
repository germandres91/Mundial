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

    def _aggregate(self) -> list[tuple]:
        """Construye las filas del ranking calculadas al vuelo y ordenadas.

        Total = puntos de partidos finalizados + bonus de posiciones finales +
        puntos provisionales de partidos EN VIVO. Devuelve una lista de tuplas
        (participant, data, bonus, live, total) ya ordenada de mayor a menor.
        """
        scoring = ScoringService(self.db)
        participants = self.participants.list()
        all_scores = self.scores.list()
        pos_points = scoring.position_points_by_participant()
        live_points = scoring.live_points_by_participant()

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

        rows: list[tuple] = []
        for participant in participants:
            data = agg[participant.id]
            bonus = pos_points.get(participant.id, 0)
            live = live_points.get(participant.id, 0)
            total = data["puntos"] + bonus + live
            rows.append((participant, data, bonus, live, total))

        rows.sort(key=lambda r: (r[4], r[1]["exactos"]), reverse=True)
        return rows

    def recalculate(self) -> list[RankingRow]:
        """Recalcula y persiste el ranking de todos los participantes.

        El total combina los puntos de partidos finalizados, el bonus de
        posiciones finales (1° a 4°) y los puntos provisionales en vivo.
        """
        aggregated = self._aggregate()
        rows: list[RankingRow] = []
        for index, (participant, data, bonus, live, total) in enumerate(aggregated, start=1):
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
                    puntos_en_vivo=live,
                    provisional=live > 0,
                )
            )
        self.db.commit()
        logger.info("Ranking recalculado para %d participantes", len(rows))
        return rows

    def get_ranking(self) -> list[RankingRow]:
        """Devuelve el ranking actual, recalculado al vuelo (incluye en vivo)."""
        rows: list[RankingRow] = []
        for index, (participant, data, bonus, live, total) in enumerate(
            self._aggregate(), start=1
        ):
            rows.append(
                RankingRow(
                    participant_id=participant.id,
                    nombre=participant.nombre,
                    puntos_totales=total,
                    posicion=index,
                    aciertos_exactos=data["exactos"],
                    partidos_acertados=data["acertados"],
                    puntos_posiciones=bonus,
                    puntos_en_vivo=live,
                    provisional=live > 0,
                )
            )
        return rows
