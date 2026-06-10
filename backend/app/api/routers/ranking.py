"""Endpoints de ranking."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.ranking import RankingRow
from app.services.ranking_service import RankingService

router = APIRouter()


@router.get("", response_model=list[RankingRow])
def get_ranking(db: Session = Depends(get_db)) -> list[RankingRow]:
    return RankingService(db).get_ranking()


@router.post("/recalculate", response_model=list[RankingRow])
def recalculate(db: Session = Depends(get_db)) -> list[RankingRow]:
    return RankingService(db).recalculate()
