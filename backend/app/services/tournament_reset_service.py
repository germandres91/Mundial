"""Reset administrativo del torneo, conservando usuarios de acceso."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.core.config import resolve_path
from app.models.match import Match
from app.models.participant import Participant
from app.models.position_prediction import PositionPrediction
from app.models.prediction import Prediction
from app.models.ranking import Ranking
from app.models.score import Score
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.ranking_service import RankingService
from app.services.tournament_service import TournamentService


class TournamentResetService:
    """Reinicia calendario/predicciones/ranking sin tocar los usuarios."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def reset_from_seed(self) -> dict:
        """Borra datos de torneo y vuelve a cargar el calendario oficial + German."""
        deleted = self._delete_tournament_data()
        schedule_created = TournamentService(self.db).seed_schedule()
        seed_result = self._load_german_seed()
        ranking = RankingService(self.db).recalculate()
        return {
            "deleted": deleted,
            "schedule_created": schedule_created,
            "seed": seed_result,
            "ranking_rows": len(ranking),
        }

    def _delete_tournament_data(self) -> dict[str, int]:
        counts = {
            "scores": self.db.query(Score).count(),
            "predictions": self.db.query(Prediction).count(),
            "position_predictions": self.db.query(PositionPrediction).count(),
            "rankings": self.db.query(Ranking).count(),
            "participants": self.db.query(Participant).count(),
            "matches": self.db.query(Match).count(),
        }
        for model in (
            Score,
            Prediction,
            PositionPrediction,
            Ranking,
            Participant,
            Match,
        ):
            self.db.query(model).delete(synchronize_session=False)
        self.db.commit()
        return counts

    def _load_german_seed(self) -> dict:
        path = resolve_path("data/german_bello_seed.json")
        if not path.exists():
            return {"loaded": False, "reason": f"No existe {path}"}

        payload = json.loads(path.read_text(encoding="utf-8"))
        participant = ParticipantRepository(self.db).create(
            nombre=payload["nombre"], email=payload["email"]
        )
        self.db.flush()

        matches = {
            (m.grupo, m.local, m.visitante): m
            for m in MatchRepository(self.db).list()
        }
        predictions = PredictionRepository(self.db)
        imported = 0
        skipped = 0
        for item in payload.get("predicciones", []):
            match = matches.get((item["grupo"], item["local"], item["visitante"]))
            if match is None:
                skipped += 1
                continue
            predictions.upsert(
                participant_id=participant.id,
                match_id=match.id,
                pred_local=int(item["pred_local"]),
                pred_visitante=int(item["pred_visitante"]),
            )
            imported += 1

        positions = PositionPredictionRepository(self.db)
        for item in payload.get("top4", []):
            positions.upsert(
                participant_id=participant.id,
                posicion=int(item["posicion"]),
                equipo=item["equipo"],
                puntos=int(item.get("puntos", 0)),
            )

        self.db.commit()
        return {
            "loaded": True,
            "participant_id": participant.id,
            "predictions_imported": imported,
            "predictions_skipped": skipped,
            "top4": len(payload.get("top4", [])),
        }
