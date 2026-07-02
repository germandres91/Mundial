"""Endpoints de partidos."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.schemas.match import MatchCreate, MatchOut, MatchResult, MatchUpdate
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService

router = APIRouter()


@router.get("", response_model=list[MatchOut])
def list_matches(
    fase: str | None = None,
    estado: MatchStatus | None = None,
    db: Session = Depends(get_db),
) -> list:
    return MatchRepository(db).list(fase=fase, estado=estado)


@router.get("/{match_id}", response_model=MatchOut)
def get_match(match_id: int, db: Session = Depends(get_db)):
    match = MatchRepository(db).get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    return match


@router.post("", response_model=MatchOut, status_code=status.HTTP_201_CREATED)
def create_match(payload: MatchCreate, db: Session = Depends(get_db)):
    match = MatchRepository(db).create(**payload.model_dump())
    db.commit()
    return match


@router.put("/{match_id}", response_model=MatchOut)
def update_match(match_id: int, payload: MatchUpdate, db: Session = Depends(get_db)):
    repo = MatchRepository(db)
    match = repo.get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(match, key, value)
    db.commit()
    return match


@router.post("/{match_id}/result", response_model=MatchOut)
def set_result(match_id: int, payload: MatchResult, db: Session = Depends(get_db)):
    """Registra el resultado de un partido y recalcula puntajes y ranking."""
    repo = MatchRepository(db)
    match = repo.get(match_id)
    if match is None:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    match.goles_local = payload.goles_local
    match.goles_visitante = payload.goles_visitante
    match.goles_local_90 = (
        payload.goles_local_90
        if payload.goles_local_90 is not None
        else payload.goles_local
    )
    match.goles_visitante_90 = (
        payload.goles_visitante_90
        if payload.goles_visitante_90 is not None
        else payload.goles_visitante
    )
    match.penales_local = payload.penales_local
    match.penales_visitante = payload.penales_visitante
    match.ganador = payload.ganador
    match.estado = payload.estado
    db.flush()

    if match.estado == MatchStatus.FINISHED:
        ScoringService(db).score_match(match)
        db.commit()
        RankingService(db).recalculate()
    else:
        db.commit()
    return match
