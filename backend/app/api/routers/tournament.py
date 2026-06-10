"""Endpoints del torneo: tabla de posiciones y bracket eliminatorio."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.tournament_service import TournamentService

router = APIRouter()


@router.get("/bracket")
def bracket(participant_id: int | None = None, db: Session = Depends(get_db)) -> dict:
    """Devuelve grupos con posiciones, clasificados, top-4 y eliminatorias.

    Si se indica `participant_id`, las posiciones se calculan con sus
    predicciones (bracket proyectado); de lo contrario, con resultados reales.
    """
    return TournamentService(db).bracket(participant_id=participant_id)


@router.post("/seed-schedule")
def seed_schedule(db: Session = Depends(get_db)) -> dict:
    """Crea el calendario del torneo desde el archivo de datos."""
    return {"partidos_creados": TournamentService(db).seed_schedule()}
