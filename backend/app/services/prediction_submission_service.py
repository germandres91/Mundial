"""Envío de predicciones de eliminatorias: una sola vez por partido, sin edición."""

from __future__ import annotations



from datetime import datetime, timezone



from sqlalchemy.orm import Session



from app.core.logging import get_logger

from app.models.late_prediction_request import LatePredictionStatus

from app.models.user import User, UserRole

from app.repositories.late_prediction_repository import LatePredictionRepository

from app.repositories.match_repository import MatchRepository

from app.repositories.participant_repository import ParticipantRepository

from app.repositories.prediction_repository import PredictionRepository

from app.services.knockout_service import KNOCKOUT_FASES, r32_display_by_fifa_id

from app.utils.datetime_fmt import utc_iso



logger = get_logger(__name__)





class PredictionSubmissionError(Exception):

    def __init__(self, message: str, code: str = "invalid") -> None:

        super().__init__(message)

        self.code = code





class PredictionSubmissionService:

    def __init__(self, db: Session) -> None:

        self.db = db

        self.matches = MatchRepository(db)

        self.predictions = PredictionRepository(db)

        self.late = LatePredictionRepository(db)

        self.participants = ParticipantRepository(db)



    def _resolve_participant_id(self, user: User, participant_id: int | None) -> int:

        if user.role == UserRole.ADMIN and participant_id is not None:

            return participant_id

        if user.participant_id is None:

            raise PredictionSubmissionError(

                "Tu cuenta no está vinculada a un participante. Contacta al administrador.",

                "no_participant",

            )

        if participant_id is not None and participant_id != user.participant_id:

            raise PredictionSubmissionError(

                "No puedes enviar predicciones de otro participante", "forbidden"

            )

        return user.participant_id



    def _is_knockout_match(self, fase: str | None) -> bool:

        if not fase:

            return False

        return fase in KNOCKOUT_FASES



    @staticmethod

    def _can_submit(pred) -> bool:

        return pred is None or pred.locked_at is None



    def submit(

        self,

        user: User,

        match_id: int,

        pred_local: int,

        pred_visitante: int,

        participant_id: int | None = None,

    ) -> dict:

        pid = self._resolve_participant_id(user, participant_id)

        match = self.matches.get(match_id)

        if match is None:

            raise PredictionSubmissionError("Partido no encontrado", "not_found")



        if not self._is_knockout_match(match.fase):

            raise PredictionSubmissionError(

                "Solo puedes enviar predicciones de partidos de eliminatorias", "not_knockout"

            )



        existing = self.predictions.get_for(pid, match_id)

        if existing is not None and existing.locked_at is not None:

            raise PredictionSubmissionError(

                "Ya enviaste tu predicción para este partido y no puede modificarse",

                "locked",

            )



        now = datetime.now(timezone.utc)

        pred = self.predictions.create_locked(pid, match_id, pred_local, pred_visitante, now)

        self.db.commit()

        return {

            "status": "submitted",

            "prediction_id": pred.id,

            "locked_at": pred.locked_at.isoformat() if pred.locked_at else None,

        }



    def approve_late(self, request_id: int, admin_user: User, note: str | None = None) -> dict:

        req = self.late.get(request_id)

        if req is None:

            raise PredictionSubmissionError("Solicitud no encontrada", "not_found")

        if req.status != LatePredictionStatus.PENDING:

            raise PredictionSubmissionError("La solicitud ya fue procesada", "already_done")



        existing = self.predictions.get_for(req.participant_id, req.match_id)

        if existing and existing.locked_at:

            raise PredictionSubmissionError("El participante ya tiene predicción bloqueada", "locked")



        now = datetime.now(timezone.utc)

        if existing:

            existing.pred_local = req.pred_local

            existing.pred_visitante = req.pred_visitante

            existing.locked_at = now

            pred = existing

        else:

            pred = self.predictions.create_locked(

                req.participant_id,

                req.match_id,

                req.pred_local,

                req.pred_visitante,

                now,

            )



        req.status = LatePredictionStatus.APPROVED

        req.reviewed_at = now

        req.reviewed_by_user_id = admin_user.id

        req.admin_note = note

        self.db.commit()

        return {"status": "approved", "prediction_id": pred.id}



    def reject_late(self, request_id: int, admin_user: User, note: str | None = None) -> dict:

        req = self.late.get(request_id)

        if req is None:

            raise PredictionSubmissionError("Solicitud no encontrada", "not_found")

        if req.status != LatePredictionStatus.PENDING:

            raise PredictionSubmissionError("La solicitud ya fue procesada", "already_done")

        req.status = LatePredictionStatus.REJECTED

        req.reviewed_at = datetime.now(timezone.utc)

        req.reviewed_by_user_id = admin_user.id

        req.admin_note = note

        self.db.commit()

        return {"status": "rejected"}



    def open_matches_for(self, user: User, participant_id: int | None = None) -> list[dict]:

        pid = self._resolve_participant_id(user, participant_id)

        knockout = [m for m in self.matches.list() if self._is_knockout_match(m.fase)]

        preds = {p.match_id: p for p in self.predictions.list(participant_id=pid)}

        display = r32_display_by_fifa_id()

        out = []

        for m in knockout:

            pred = preds.get(m.id)

            meta = display.get(m.fifa_id or "", {})

            out.append(

                {

                    "match_id": m.id,

                    "fifa_id": m.fifa_id,

                    "fase": m.fase,

                    "local": m.local,

                    "visitante": m.visitante,

                    "fecha": utc_iso(m.fecha),

                    "fecha_dia_colombia": meta.get("fecha_dia_colombia"),

                    "hora_colombia": meta.get("hora_colombia"),

                    "estado": m.estado.value,

                    "can_submit": self._can_submit(pred),

                    "submitted": pred is not None and pred.locked_at is not None,

                    "pred_local": pred.pred_local if pred else None,

                    "pred_visitante": pred.pred_visitante if pred else None,

                    "locked_at": pred.locked_at.isoformat() if pred and pred.locked_at else None,

                }

            )

        return sorted(out, key=lambda x: (x["fase"] or "", x["fecha"] or ""))



    def submission_matrix(self, fase: str | None = None) -> dict:

        """Matriz participante × partido para el panel admin."""

        participants = self.participants.list()

        matches = (

            [m for m in self.matches.list(fase=fase) if self._is_knockout_match(m.fase)]

            if fase

            else [m for m in self.matches.list() if self._is_knockout_match(m.fase)]

        )



        all_preds = self.predictions.list()

        pred_map = {(p.participant_id, p.match_id): p for p in all_preds}



        rows = []

        for p in participants:

            cells = []

            for m in matches:

                pred = pred_map.get((p.id, m.id))

                cells.append(

                    {

                        "match_id": m.id,

                        "submitted": pred is not None and pred.locked_at is not None,

                        "pred_local": pred.pred_local if pred else None,

                        "pred_visitante": pred.pred_visitante if pred else None,

                    }

                )

            rows.append({"participant_id": p.id, "nombre": p.nombre, "cells": cells})



        return {

            "matches": [

                {

                    "id": m.id,

                    "fifa_id": m.fifa_id,

                    "fase": m.fase,

                    "local": m.local,

                    "visitante": m.visitante,

                    "fecha": utc_iso(m.fecha),

                    **r32_display_by_fifa_id().get(m.fifa_id or "", {}),

                    "estado": m.estado.value,

                }

                for m in matches

            ],

            "participants": rows,

        }


