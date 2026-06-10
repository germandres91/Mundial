"""Repositorio de predicciones."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.prediction import Prediction


class PredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self, participant_id: int | None = None, match_id: int | None = None
    ) -> list[Prediction]:
        stmt = select(Prediction)
        if participant_id:
            stmt = stmt.where(Prediction.participant_id == participant_id)
        if match_id:
            stmt = stmt.where(Prediction.match_id == match_id)
        return list(self.db.scalars(stmt))

    def get(self, prediction_id: int) -> Prediction | None:
        return self.db.get(Prediction, prediction_id)

    def get_for(self, participant_id: int, match_id: int) -> Prediction | None:
        return self.db.scalar(
            select(Prediction).where(
                Prediction.participant_id == participant_id,
                Prediction.match_id == match_id,
            )
        )

    def list_for_match(self, match_id: int) -> list[Prediction]:
        return list(
            self.db.scalars(select(Prediction).where(Prediction.match_id == match_id))
        )

    def upsert(
        self, participant_id: int, match_id: int, pred_local: int, pred_visitante: int
    ) -> Prediction:
        existing = self.get_for(participant_id, match_id)
        if existing:
            existing.pred_local = pred_local
            existing.pred_visitante = pred_visitante
            self.db.flush()
            return existing
        prediction = Prediction(
            participant_id=participant_id,
            match_id=match_id,
            pred_local=pred_local,
            pred_visitante=pred_visitante,
        )
        self.db.add(prediction)
        self.db.flush()
        return prediction

    def count(self) -> int:
        return int(self.db.scalar(select(func.count()).select_from(Prediction)) or 0)

    def delete(self, prediction: Prediction) -> None:
        self.db.delete(prediction)
        self.db.flush()
