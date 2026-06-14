"""Servicio de agregación para dashboard y estadísticas."""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.ranking_repository import RankingRepository
from app.repositories.score_repository import ScoreRepository
from app.schemas.dashboard import (
    ChartPoint,
    DashboardSummary,
    ParticipantStats,
    RaceMatch,
    RaceResponse,
    RaceSeries,
)
from app.schemas.match import MatchOut
from app.schemas.ranking import RankingRow


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.matches = MatchRepository(db)
        self.participants = ParticipantRepository(db)
        self.predictions = PredictionRepository(db)
        self.rankings = RankingRepository(db)
        self.scores = ScoreRepository(db)

    def summary(self) -> DashboardSummary:
        leader = self.rankings.leader()
        leader_row = None
        if leader and leader.participant:
            leader_row = RankingRow(
                participant_id=leader.participant_id,
                nombre=leader.participant.nombre,
                puntos_totales=leader.puntos_totales,
                posicion=leader.posicion,
                aciertos_exactos=leader.aciertos_exactos,
                partidos_acertados=leader.partidos_acertados,
            )

        next_match = self.matches.next_match()
        last = self.matches.last_finished()

        return DashboardSummary(
            proximo_partido=MatchOut.model_validate(next_match) if next_match else None,
            ultimo_resultado=MatchOut.model_validate(last) if last else None,
            lider=leader_row,
            partidos_jugados=self.matches.count(MatchStatus.FINISHED),
            partidos_pendientes=self.matches.count(MatchStatus.SCHEDULED),
            total_partidos=self.matches.count(),
            total_participantes=len(self.participants.list()),
            total_predicciones=self.predictions.count(),
        )

    def participant_stats(self, participant_id: int) -> ParticipantStats | None:
        participant = self.participants.get(participant_id)
        if participant is None:
            return None

        ranking = self.rankings.get(participant_id)
        scores = self.scores.list(participant_id=participant_id)

        por_fase: dict[str, float] = defaultdict(float)
        for score in scores:
            fase = score.match.fase if score.match else "General"
            por_fase[fase or "General"] += score.puntos

        return ParticipantStats(
            participant_id=participant.id,
            nombre=participant.nombre,
            puntos_totales=ranking.puntos_totales if ranking else 0,
            aciertos_exactos=ranking.aciertos_exactos if ranking else 0,
            partidos_acertados=ranking.partidos_acertados if ranking else 0,
            puntos_por_fase=[ChartPoint(label=k, value=v) for k, v in por_fase.items()],
        )

    def hits_per_participant(self) -> list[ChartPoint]:
        """Aciertos (predicciones con puntos > 0) por participante."""
        result: list[ChartPoint] = []
        for ranking in self.rankings.list():
            nombre = ranking.participant.nombre if ranking.participant else "?"
            result.append(ChartPoint(label=nombre, value=ranking.partidos_acertados))
        return result

    def points_per_phase(self) -> list[ChartPoint]:
        """Suma de puntos de todos los participantes por fase del torneo."""
        por_fase: dict[str, float] = defaultdict(float)
        for score in self.scores.list():
            fase = score.match.fase if score.match else "General"
            por_fase[fase or "General"] += score.puntos
        return [ChartPoint(label=k, value=v) for k, v in por_fase.items()]

    def race_to_cup(self) -> RaceResponse:
        """Puntaje acumulado de cada participante partido a partido.

        El eje X son los partidos jugados (FINISHED) en orden cronológico y el
        eje Y el puntaje acumulado. Permite ver cómo cambia el liderato a lo
        largo del torneo.
        """
        played = [
            m for m in self.matches.list() if m.estado == MatchStatus.FINISHED
        ]
        partidos = [
            RaceMatch(
                orden=i,
                match_id=m.id,
                etiqueta=f"{m.local} vs {m.visitante}",
                fase=m.fase or "",
                fecha=m.fecha,
            )
            for i, m in enumerate(played, start=1)
        ]

        score_map: dict[tuple[int, int], int] = {}
        for s in self.scores.list():
            score_map[(s.participant_id, s.match_id)] = s.puntos

        series: list[RaceSeries] = []
        for p in self.participants.list():
            acumulado = 0
            puntos: list[int] = []
            for m in played:
                acumulado += score_map.get((p.id, m.id), 0)
                puntos.append(acumulado)
            series.append(
                RaceSeries(participant_id=p.id, nombre=p.nombre, puntos=puntos)
            )

        # Ordena las series por puntaje final (desc) para una leyenda intuitiva.
        series.sort(key=lambda s: s.puntos[-1] if s.puntos else 0, reverse=True)
        return RaceResponse(partidos=partidos, series=series)
