"""Endpoints de predicciones de eliminatorias (participantes)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.round_prediction import RoundPredictionSubmit
from app.services.prediction_submission_service import (
    PredictionSubmissionError,
    PredictionSubmissionService,
)

router = APIRouter()


def _handle_error(exc: PredictionSubmissionError) -> HTTPException:
    status = 400
    if exc.code == "not_found":
        status = 404
    elif exc.code == "forbidden":
        status = 403
    elif exc.code in ("locked",):
        status = 409
    return HTTPException(status_code=status, detail=str(exc))


@router.get("/matches")
def my_knockout_matches(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list:
    """Partidos de eliminatorias y estado de predicción del usuario."""
    return PredictionSubmissionService(db).open_matches_for(user)


@router.post("/submit")
def submit_round_prediction(
    payload: RoundPredictionSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Envía una predicción (una sola vez). Fuera de plazo → pendiente de aprobación."""
    try:
        return PredictionSubmissionService(db).submit(
            user,
            payload.match_id,
            payload.pred_local,
            payload.pred_visitante,
        )
    except PredictionSubmissionError as exc:
        raise _handle_error(exc) from exc
