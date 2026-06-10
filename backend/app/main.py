"""Punto de entrada de la API FastAPI (Mundial 2026)."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.routers import api_router
from app.bootstrap import bootstrap
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.jobs.scheduler import shutdown_scheduler, start_scheduler

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando %s v%s [%s]", settings.app_name, __version__, settings.environment)
    bootstrap()
    start_scheduler()
    yield
    shutdown_scheduler()
    logger.info("Aplicación detenida")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="Plataforma profesional de predicciones del Mundial 2026.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


@app.get("/", tags=["Salud"])
def root() -> dict:
    return {"app": settings.app_name, "version": __version__, "status": "ok"}


@app.get("/health", tags=["Salud"])
def health() -> dict:
    return {"status": "healthy", "environment": settings.environment}


app.include_router(api_router, prefix=settings.api_v1_prefix)
