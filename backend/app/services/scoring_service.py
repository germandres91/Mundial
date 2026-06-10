"""Servicio de cálculo de puntajes según las reglas del concurso."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.match import Match
from app.repositories.match_repository import MatchRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.scoring_rule_repository import ScoringRuleRepository

logger = get_logger(__name__)

# Reglas por defecto si no hay nada en la base de datos / Excel.
DEFAULT_RULES: dict[str, int] = {
    "EXACT": 5,        # Marcador exacto
    "WINNER_GOALS": 3, # Ganador + goles del ganador
    "WINNER": 2,       # Ganador correcto
    "DRAW": 1,         # Empate correcto
    "NONE": 0,         # Sin acierto
}


@dataclass
class ScoreResult:
    code: str
    puntos: int
    detalle: str


class ScoringService:
    """Calcula puntos comparando predicciones contra resultados reales."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.predictions = PredictionRepository(db)
        self.scores = ScoreRepository(db)
        self.matches = MatchRepository(db)
        self.rules = ScoringRuleRepository(db)

    def _points_map(self) -> dict[str, int]:
        configured = self.rules.as_points_map()
        return {**DEFAULT_RULES, **configured}

    @staticmethod
    def _outcome(local: int, visitante: int) -> str:
        if local > visitante:
            return "LOCAL"
        if local < visitante:
            return "VISITANTE"
        return "EMPATE"

    def evaluate(
        self,
        pred_local: int,
        pred_visitante: int,
        real_local: int,
        real_visitante: int,
        points: dict[str, int] | None = None,
    ) -> ScoreResult:
        """Evalúa una predicción individual y devuelve el puntaje obtenido."""
        pts = points or self._points_map()

        # 1. Marcador exacto
        if pred_local == real_local and pred_visitante == real_visitante:
            return ScoreResult("EXACT", pts["EXACT"], "Marcador exacto")

        pred_outcome = self._outcome(pred_local, pred_visitante)
        real_outcome = self._outcome(real_local, real_visitante)

        # Resultado distinto => sin acierto
        if pred_outcome != real_outcome:
            return ScoreResult("NONE", pts["NONE"], "Sin acierto")

        # Acertó el resultado (empate o ganador)
        if real_outcome == "EMPATE":
            return ScoreResult("DRAW", pts["DRAW"], "Empate correcto")

        # Acertó al ganador: ¿también los goles del ganador?
        winner_goals_real = real_local if real_outcome == "LOCAL" else real_visitante
        winner_goals_pred = pred_local if real_outcome == "LOCAL" else pred_visitante
        if winner_goals_real == winner_goals_pred:
            return ScoreResult("WINNER_GOALS", pts["WINNER_GOALS"], "Ganador + goles del ganador")

        return ScoreResult("WINNER", pts["WINNER"], "Ganador correcto")

    def score_match(self, match: Match) -> int:
        """Calcula y persiste los puntajes de todas las predicciones de un partido.

        Devuelve el número de predicciones evaluadas.
        """
        if not match.is_finished or match.goles_local is None or match.goles_visitante is None:
            return 0

        points = self._points_map()
        predictions = self.predictions.list_for_match(match.id)
        for pred in predictions:
            result = self.evaluate(
                pred.pred_local,
                pred.pred_visitante,
                match.goles_local,
                match.goles_visitante,
                points,
            )
            self.scores.upsert(
                participant_id=pred.participant_id,
                match_id=match.id,
                puntos=result.puntos,
                detalle=result.detalle,
            )
        logger.info("Partido %s puntuado: %d predicciones", match.id, len(predictions))
        return len(predictions)

    def recalculate_all(self) -> int:
        """Recalcula puntajes de todos los partidos finalizados."""
        total = 0
        for match in self.matches.finished_matches():
            total += self.score_match(match)
        self.db.commit()
        return total
