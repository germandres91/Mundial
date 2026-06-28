"""Envío de predicciones por ronda: una vez, antes del partido, con aprobación tardía."""
from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.late_prediction_request import LatePredictionStatus
from app.models.match import MatchStatus
from app.models.user import User, UserRole
from app.repositories.late_prediction_repository import LatePredictionRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.knockout_service import (
    KNOCKOUT_FASES,
    r32_display_by_fifa_id,
    r32_grace_submit_days,
    r32_late_submit_allowed,
)
from app.utils.datetime_fmt import utc_iso

logger = get_logger(__name__)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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

    def _in_grace_day(self, match) -> bool:
        if not match.fifa_id:
            return False
        grace = r32_grace_submit_days().get(match.fifa_id)
        if grace is None:
            return False
        now_col = datetime.now(ZoneInfo("America/Bogota")).date()
        return now_col == grace

    def _late_submit_allowed(self, match) -> bool:
        if not match.fifa_id:
            return False
        return match.fifa_id in r32_late_submit_allowed()

    def _kickoff_open(self, match) -> bool:
        """Envío inmediato (sin aprobación del admin)."""
        if match.estado != MatchStatus.SCHEDULED:
            return False

        if self._in_grace_day(match):
            return True

        if match.fecha is None:
            return True
        cutoff = _as_utc(match.fecha)
        if settings.prediction_cutoff_minutes:
            from datetime import timedelta

            cutoff = cutoff - timedelta(minutes=settings.prediction_cutoff_minutes)
        return datetime.now(timezone.utc) < cutoff

    def _requires_approval(self, match) -> bool:
        return not self._kickoff_open(match)

    def _can_submit(self, match, pred, pending_req) -> bool:
        if pred is not None and pred.locked_at is not None:
            return False
        if pending_req is not None:
            return False
        if self._late_submit_allowed(match):
            return True
        if match.estado != MatchStatus.SCHEDULED:
            return False
        return True

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

        pending = self.late.get_for(pid, match_id)
        if pending and pending.status == LatePredictionStatus.PENDING:
            raise PredictionSubmissionError(
                "Tienes una solicitud pendiente de aprobación para este partido",
                "pending",
            )

        if match.estado in (MatchStatus.LIVE, MatchStatus.FINISHED) and not self._late_submit_allowed(
            match
        ):
            raise PredictionSubmissionError(
                "El partido ya se jugó; no se aceptan predicciones.",
                "closed",
            )

        if self._kickoff_open(match):
            now = datetime.now(timezone.utc)
            pred = self.predictions.create_locked(pid, match_id, pred_local, pred_visitante, now)
            self.db.commit()
            return {
                "status": "submitted",
                "prediction_id": pred.id,
                "locked_at": pred.locked_at.isoformat() if pred.locked_at else None,
            }

        # Fuera de plazo → solicitud al admin
        req = self.late.upsert_pending(pid, match_id, pred_local, pred_visitante)
        self.db.commit()
        return {
            "status": "pending_approval",
            "request_id": req.id,
            "message": "Fuera de plazo. Tu predicción quedó pendiente de aprobación del administrador.",
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
        knockout = [
            m
            for m in self.matches.list()
            if self._is_knockout_match(m.fase)
        ]
        preds = {p.match_id: p for p in self.predictions.list(participant_id=pid)}
        pending = {
            r.match_id: r
            for r in self.late.list()
            if r.participant_id == pid and r.status == LatePredictionStatus.PENDING
        }
        display = r32_display_by_fifa_id()
        out = []
        for m in knockout:
            pred = preds.get(m.id)
            pend = pending.get(m.id)
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
                    "can_submit": self._can_submit(m, pred, pend),
                    "requires_approval": self._requires_approval(m),
                    "late_submit_allowed": self._late_submit_allowed(m),
                    "submitted": pred is not None and pred.locked_at is not None,
                    "pred_local": pred.pred_local if pred else None,
                    "pred_visitante": pred.pred_visitante if pred else None,
                    "locked_at": pred.locked_at.isoformat() if pred and pred.locked_at else None,
                    "pending_approval": pend is not None,
                    "kickoff_open": self._kickoff_open(m),
                }
            )
        return sorted(out, key=lambda x: (x["fase"] or "", x["fecha"] or ""))

    def submission_matrix(self, fase: str | None = None) -> dict:
        """Matriz participante × partido para el panel admin."""
        participants = self.participants.list()
        matches = [
            m
            for m in self.matches.list(fase=fase)
            if self._is_knockout_match(m.fase)
        ] if fase else [m for m in self.matches.list() if self._is_knockout_match(m.fase)]

        all_preds = self.predictions.list()
        pred_map = {(p.participant_id, p.match_id): p for p in all_preds}
        pending = {
            (r.participant_id, r.match_id): r
            for r in self.late.list(status=LatePredictionStatus.PENDING)
        }

        rows = []
        for p in participants:
            cells = []
            for m in matches:
                pred = pred_map.get((p.id, m.id))
                pend = pending.get((p.id, m.id))
                cells.append(
                    {
                        "match_id": m.id,
                        "submitted": pred is not None and pred.locked_at is not None,
                        "pending": pend is not None,
                        "request_id": pend.id if pend else None,
                        "pred_local": pred.pred_local if pred else None,
                        "pred_visitante": pred.pred_visitante if pred else None,
                        "pending_pred_local": pend.pred_local if pend else None,
                        "pending_pred_visitante": pend.pred_visitante if pend else None,
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
