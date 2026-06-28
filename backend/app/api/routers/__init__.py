"""Routers de la API v1.

Modelo de acceso:
- `/auth/*` es público (login).
- El resto exige sesión iniciada para LEER; solo el administrador puede MODIFICAR
  (control por método HTTP en `access_control`).
- `/admin/*` es exclusivo del administrador (lectura y escritura).
"""
from fastapi import APIRouter, Depends

from app.api.deps import access_control, get_current_user, require_admin
from app.api.routers import (
    admin,
    auth,
    dashboard,
    export,
    matches,
    participants,
    predictions,
    ranking,
    round_predictions,
    stats,
    tournament,
)

api_router = APIRouter()

# Público
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación"])

# Predicciones de eliminatorias (lectura/escritura del propio participante)
api_router.include_router(
    round_predictions.router,
    prefix="/round-predictions",
    tags=["Eliminatorias"],
    dependencies=[Depends(get_current_user)],
)

# Requiere sesión (leer todos, escribir solo admin)
protected = APIRouter(dependencies=[Depends(access_control)])
protected.include_router(participants.router, prefix="/participants", tags=["Participantes"])
protected.include_router(matches.router, prefix="/matches", tags=["Partidos"])
protected.include_router(predictions.router, prefix="/predictions", tags=["Predicciones"])
protected.include_router(ranking.router, prefix="/ranking", tags=["Ranking"])
protected.include_router(tournament.router, prefix="/tournament", tags=["Torneo"])
protected.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
protected.include_router(stats.router, prefix="/stats", tags=["Estadísticas"])
protected.include_router(export.router, prefix="/export", tags=["Exportación"])
api_router.include_router(protected)

# Solo administrador
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Administración"],
    dependencies=[Depends(require_admin)],
)

__all__ = ["api_router"]
