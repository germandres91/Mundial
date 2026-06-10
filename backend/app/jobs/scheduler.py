"""Configuración del planificador de tareas (APScheduler)."""
from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.services.sync_service import SyncService

logger = get_logger(__name__)

_scheduler: BackgroundScheduler | None = None


def sync_job() -> None:
    """Job ejecutado periódicamente: sincroniza resultados y recalcula todo."""
    db = SessionLocal()
    try:
        result = SyncService(db).sync()
        logger.info("Job de sincronización ejecutado: %s", result)
    except Exception:  # noqa: BLE001 - el scheduler no debe morir por un fallo puntual
        logger.exception("Error en el job de sincronización")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Inicia el scheduler si la automatización está habilitada."""
    global _scheduler
    if not settings.sync_enabled:
        logger.info("Automatización deshabilitada (SYNC_ENABLED=false)")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        sync_job,
        trigger="interval",
        minutes=settings.sync_interval_minutes,
        id="sync_results",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler iniciado: sincronización cada %d minutos", settings.sync_interval_minutes
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Detiene el scheduler de forma segura."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
    _scheduler = None
