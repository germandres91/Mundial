"""Servicio de cálculo de puntajes según las reglas del concurso."""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.match import Match
from app.repositories.final_position_repository import FinalPositionRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.scoring_rule_repository import ScoringRuleRepository
from app.utils.teams import team_code

logger = get_logger(__name__)

# Reglas por defecto si no hay nada en la base de datos / Excel.
DEFAULT_RULES: dict[str, int] = {
    "EXACT": 5,        # Marcador exacto
    "WINNER_GOALS": 3, # Ganador + goles del ganador
    "WINNER": 2,       # Ganador correcto
    "DRAW": 1,         # Empate correcto
    "NONE": 0,         # Sin acierto
    # Bonus por acertar las posiciones finales (al terminar el Mundial)
    "POS_1": 10,       # Campeón
    "POS_2": 9,        # Subcampeón
    "POS_3": 7,        # Tercer puesto
    "POS_4": 5,        # Cuarto puesto
}

# Descripciones legibles de cada regla (usadas al sembrar por defecto).
RULE_DESCRIPTIONS: dict[str, str] = {
    "EXACT": "Marcador exacto",
    "WINNER_GOALS": "Ganador + goles del ganador",
    "WINNER": "Ganador correcto",
    "DRAW": "Empate correcto",
    "NONE": "Sin acierto",
    "POS_1": "Acierto 1er puesto (Campeón)",
    "POS_2": "Acierto 2do puesto (Subcampeón)",
    "POS_3": "Acierto 3er puesto",
    "POS_4": "Acierto 4to puesto",
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
        self.positions = PositionPredictionRepository(db)
        self.final_positions = FinalPositionRepository(db)

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

    def live_points_by_participant(self) -> dict[int, int]:
        """Puntos provisionales por participante de los partidos EN VIVO.

        Se calcula al vuelo (no se persiste) usando el marcador actual de los
        partidos en juego. Cuando un partido finaliza, sus puntos pasan a la
        tabla de puntajes (definitivos) vía `score_match` y dejan de contarse
        como provisionales.
        """
        from app.models.match import MatchStatus

        points = self._points_map()
        acc: dict[int, int] = {}
        for match in self.matches.list(estado=MatchStatus.LIVE):
            if match.goles_local is None or match.goles_visitante is None:
                continue
            for pred in self.predictions.list_for_match(match.id):
                result = self.evaluate(
                    pred.pred_local,
                    pred.pred_visitante,
                    match.goles_local,
                    match.goles_visitante,
                    points,
                )
                if result.puntos:
                    acc[pred.participant_id] = acc.get(pred.participant_id, 0) + result.puntos
        return acc

    def recalculate_all(self) -> int:
        """Recalcula puntajes de todos los partidos finalizados (acumulativo).

        Solo actualiza partidos con marcador oficial; no borra puntajes de otras
        fases ni de partidos que ya no estén finalizados.
        """
        total = 0
        for match in self.matches.finished_matches():
            total += self.score_match(match)
        self.db.commit()
        return total

    def position_points_by_participant(self) -> dict[int, int]:
        """Bonus de posiciones por participante, calculado contra el resultado real.

        Solo otorga puntos por los puestos que ya tienen resultado oficial
        registrado (FinalPosition). Si aún no se registra ningún puesto,
        devuelve un diccionario vacío (bonus 0 para todos). Esto permite el
        otorgamiento parcial: p. ej. 3° y 4° tras semifinales y 1° y 2° tras
        la final.
        """
        real = self.final_positions.as_map()  # {1: equipo, ...}
        if not real:
            return {}
        real_codes = {pos: team_code(eq) or eq.lower() for pos, eq in real.items()}
        points = self._points_map()

        acc: dict[int, int] = {}
        for pred in self.positions.list_all():
            real_code = real_codes.get(pred.posicion)
            if not real_code:
                continue
            pred_code = team_code(pred.equipo) or pred.equipo.lower()
            if pred_code == real_code:
                acc[pred.participant_id] = acc.get(pred.participant_id, 0) + points.get(
                    f"POS_{pred.posicion}", 0
                )
        return acc

    def score_positions(self) -> int:
        """Puntúa los pronósticos de posiciones finales (1° a 4°).

        Compara el equipo pronosticado por cada participante para cada puesto
        contra el resultado oficial (FinalPosition) y persiste los puntos en
        cada pronóstico (para mostrarlos por participante). Si un puesto aún no
        tiene resultado, ese pronóstico queda en 0. Devuelve el total de
        aciertos registrados.
        """
        real = self.final_positions.as_map()  # {1: equipo, ...}
        real_codes = {pos: team_code(eq) or eq.lower() for pos, eq in real.items()}
        points = self._points_map()

        aciertos = 0
        for pred in self.positions.list_all():
            real_code = real_codes.get(pred.posicion)
            if not real_code:
                # Aún no hay resultado oficial para ese puesto.
                if pred.puntos:
                    pred.puntos = 0
                continue
            pred_code = team_code(pred.equipo) or pred.equipo.lower()
            if pred_code == real_code:
                pred.puntos = points.get(f"POS_{pred.posicion}", 0)
                aciertos += 1
            else:
                pred.puntos = 0
        self.db.flush()
        logger.info("Posiciones finales puntuadas: %d aciertos", aciertos)
        return aciertos
