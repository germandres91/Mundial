"""Endpoints de predicciones."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.prediction import PredictionCreate, PredictionOut
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService

router = APIRouter()


@router.get("", response_model=list[PredictionOut])
def list_predictions(
    participant_id: int | None = None,
    match_id: int | None = None,
    db: Session = Depends(get_db),
) -> list:
    return PredictionRepository(db).list(participant_id=participant_id, match_id=match_id)


@router.post("", response_model=PredictionOut, status_code=status.HTTP_201_CREATED)
def create_prediction(payload: PredictionCreate, db: Session = Depends(get_db)):
    """Crea o actualiza una predicción (solo administrador vía access_control)."""
    if ParticipantRepository(db).get(payload.participant_id) is None:
        raise HTTPException(status_code=404, detail="Participante no encontrado")

    match = MatchRepository(db).get(payload.match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    if match.estado not in (
        MatchStatus.SCHEDULED,
        MatchStatus.LIVE,
        MatchStatus.FINISHED,
    ):
        raise HTTPException(
            status_code=400,
            detail="No se puede predecir un partido en este estado",
        )

    repo = PredictionRepository(db)
    existing = repo.get_for(payload.participant_id, payload.match_id)
    locked_at = existing.locked_at if existing else None
    if locked_at is None and match.estado != MatchStatus.SCHEDULED:
        locked_at = datetime.now(timezone.utc)

    prediction = repo.upsert(
        participant_id=payload.participant_id,
        match_id=payload.match_id,
        pred_local=payload.pred_local,
        pred_visitante=payload.pred_visitante,
        locked_at=locked_at,
    )
    db.flush()

    if match.estado == MatchStatus.FINISHED:
        ScoringService(db).score_match(match)
        db.commit()
        RankingService(db).recalculate()
    else:
        db.commit()
    return prediction


@router.delete("/{prediction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prediction(prediction_id: int, db: Session = Depends(get_db)):
    repo = PredictionRepository(db)
    prediction = repo.get(prediction_id)
    if prediction is None:
        raise HTTPException(status_code=404, detail="Predicción no encontrada")
    repo.delete(prediction)
    db.commit()
