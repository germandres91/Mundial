"""Endpoints de participantes (modo single-user, sin autenticación)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.schemas.participant import ParticipantCreate, ParticipantOut, ParticipantUpdate
from app.services.participant_import_service import ParticipantImportService
from app.services.ranking_service import RankingService

router = APIRouter()


@router.get("", response_model=list[ParticipantOut])
def list_participants(db: Session = Depends(get_db)) -> list:
    return ParticipantRepository(db).list()


@router.get("/{participant_id}", response_model=ParticipantOut)
def get_participant(participant_id: int, db: Session = Depends(get_db)):
    participant = ParticipantRepository(db).get(participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    return participant


@router.get("/{participant_id}/top4")
def get_top4(participant_id: int, db: Session = Depends(get_db)) -> list:
    rows = PositionPredictionRepository(db).list_for(participant_id)
    return [{"posicion": r.posicion, "equipo": r.equipo, "puntos": r.puntos} for r in rows]


@router.post("", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
def create_participant(payload: ParticipantCreate, db: Session = Depends(get_db)):
    repo = ParticipantRepository(db)
    if repo.get_by_email(payload.email):
        raise HTTPException(status_code=409, detail="El email ya está registrado")
    participant = repo.create(nombre=payload.nombre, email=payload.email)
    db.commit()
    return participant


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_participant(
    nombre: str = Form(...),
    email: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Crea/actualiza un participante cargando su formulario Excel (.xlsm/.xlsx)."""
    if not file.filename.lower().endswith((".xlsm", ".xlsx")):
        raise HTTPException(status_code=400, detail="El archivo debe ser .xlsm o .xlsx")
    content = await file.read()
    try:
        result = ParticipantImportService(db).import_formulario(content, nombre, email)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    RankingService(db).recalculate()
    return result


@router.put("/{participant_id}", response_model=ParticipantOut)
def update_participant(
    participant_id: int, payload: ParticipantUpdate, db: Session = Depends(get_db)
):
    repo = ParticipantRepository(db)
    participant = repo.get(participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    if payload.nombre is not None:
        participant.nombre = payload.nombre
    if payload.email is not None:
        participant.email = payload.email
    db.commit()
    return participant


@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(participant_id: int, db: Session = Depends(get_db)):
    repo = ParticipantRepository(db)
    participant = repo.get(participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    repo.delete(participant)
    db.commit()
