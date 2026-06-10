"""Endpoints de predicciones."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.prediction_repository import PredictionRepository
from app.schemas.prediction import PredictionCreate, PredictionOut

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
    if ParticipantRepository(db).get(payload.participant_id) is None:
        raise HTTPException(status_code=404, detail="Participante no encontrado")

    match = MatchRepository(db).get(payload.match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    if match.estado != MatchStatus.SCHEDULED:
        raise HTTPException(
            status_code=400, detail="No se puede predecir un partido ya iniciado o finalizado"
        )

    prediction = PredictionRepository(db).upsert(
        participant_id=payload.participant_id,
        match_id=payload.match_id,
        pred_local=payload.pred_local,
        pred_visitante=payload.pred_visitante,
    )
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
