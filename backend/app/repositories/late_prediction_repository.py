"""Repositorio de solicitudes de predicción tardía."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.late_prediction_request import LatePredictionRequest, LatePredictionStatus


class LatePredictionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, status: LatePredictionStatus | None = None) -> list[LatePredictionRequest]:
        stmt = select(LatePredictionRequest).order_by(LatePredictionRequest.created_at.desc())
        if status:
            stmt = stmt.where(LatePredictionRequest.status == status)
        return list(self.db.scalars(stmt))

    def get(self, request_id: int) -> LatePredictionRequest | None:
        return self.db.get(LatePredictionRequest, request_id)

    def get_for(self, participant_id: int, match_id: int) -> LatePredictionRequest | None:
        return self.db.scalar(
            select(LatePredictionRequest).where(
                LatePredictionRequest.participant_id == participant_id,
                LatePredictionRequest.match_id == match_id,
            )
        )

    def upsert_pending(
        self,
        participant_id: int,
        match_id: int,
        pred_local: int,
        pred_visitante: int,
    ) -> LatePredictionRequest:
        existing = self.get_for(participant_id, match_id)
        if existing:
            if existing.status == LatePredictionStatus.APPROVED:
                raise ValueError("La solicitud ya fue aprobada")
            if existing.status == LatePredictionStatus.PENDING:
                existing.pred_local = pred_local
                existing.pred_visitante = pred_visitante
                self.db.flush()
                return existing
            # Rejected: allow new pending request
            existing.status = LatePredictionStatus.PENDING
            existing.pred_local = pred_local
            existing.pred_visitante = pred_visitante
            existing.reviewed_at = None
            existing.reviewed_by_user_id = None
            existing.admin_note = None
            self.db.flush()
            return existing
        req = LatePredictionRequest(
            participant_id=participant_id,
            match_id=match_id,
            pred_local=pred_local,
            pred_visitante=pred_visitante,
            status=LatePredictionStatus.PENDING,
        )
        self.db.add(req)
        self.db.flush()
        return req
