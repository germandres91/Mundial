"""Repositorio de pronósticos de puestos finales."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.position_prediction import PositionPrediction


class PositionPredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for(self, participant_id: int) -> list[PositionPrediction]:
        return list(
            self.db.scalars(
                select(PositionPrediction)
                .where(PositionPrediction.participant_id == participant_id)
                .order_by(PositionPrediction.posicion)
            )
        )

    def list_all(self) -> list[PositionPrediction]:
        return list(
            self.db.scalars(
                select(PositionPrediction).order_by(
                    PositionPrediction.participant_id, PositionPrediction.posicion
                )
            )
        )

    def upsert(
        self, participant_id: int, posicion: int, equipo: str, puntos: int
    ) -> PositionPrediction:
        existing = self.db.scalar(
            select(PositionPrediction).where(
                PositionPrediction.participant_id == participant_id,
                PositionPrediction.posicion == posicion,
            )
        )
        if existing:
            existing.equipo = equipo
            existing.puntos = puntos
            self.db.flush()
            return existing
        pred = PositionPrediction(
            participant_id=participant_id, posicion=posicion, equipo=equipo, puntos=puntos
        )
        self.db.add(pred)
        self.db.flush()
        return pred
