"""Routers de la API v1."""
from fastapi import APIRouter

from app.api.routers import (
    admin,
    auth,
    dashboard,
    export,
    matches,
    participants,
    predictions,
    ranking,
    stats,
    tournament,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])
api_router.include_router(participants.router, prefix="/participants", tags=["Participantes"])
api_router.include_router(matches.router, prefix="/matches", tags=["Partidos"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["Predicciones"])
api_router.include_router(ranking.router, prefix="/ranking", tags=["Ranking"])
api_router.include_router(tournament.router, prefix="/tournament", tags=["Torneo"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(stats.router, prefix="/stats", tags=["Estadísticas"])
api_router.include_router(export.router, prefix="/export", tags=["Exportación"])
api_router.include_router(admin.router, prefix="/admin", tags=["Administración"])

__all__ = ["api_router"]
