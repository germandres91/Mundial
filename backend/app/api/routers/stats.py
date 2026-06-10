"""Endpoints de estadísticas y datos para gráficas."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.dashboard import ChartPoint, ParticipantStats
from app.services.dashboard_service import DashboardService

router = APIRouter()


@router.get("/hits", response_model=list[ChartPoint])
def hits_per_participant(db: Session = Depends(get_db)) -> list[ChartPoint]:
    """Aciertos por participante."""
    return DashboardService(db).hits_per_participant()


@router.get("/phases", response_model=list[ChartPoint])
def points_per_phase(db: Session = Depends(get_db)) -> list[ChartPoint]:
    """Rendimiento (puntos) por fase del torneo."""
    return DashboardService(db).points_per_phase()


@router.get("/participant/{participant_id}", response_model=ParticipantStats)
def participant_stats(participant_id: int, db: Session = Depends(get_db)) -> ParticipantStats:
    stats = DashboardService(db).participant_stats(participant_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Participante no encontrado")
    return stats
