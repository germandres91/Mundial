"""Configuración del planificador de tareas (APScheduler).

Usa un intervalo inteligente: cuando hay un partido en vivo (o a punto de
empezar) sincroniza cada `sync_live_seconds`; el resto del tiempo lo hace cada
`sync_interval_minutes`. El job se reprograma a sí mismo tras cada ejecución.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.services.sync_service import SyncService

logger = get_logger(__name__)

_JOB_ID = "sync_results"
_scheduler: BackgroundScheduler | None = None
_current_seconds: int | None = None


def _decide_interval(db: Session) -> tuple[str, int]:
    """Devuelve (modo, segundos) según haya partidos en vivo o inminentes."""
    repo = MatchRepository(db)
    if repo.count(MatchStatus.LIVE) > 0:
        return ("vivo", settings.sync_live_seconds)

    nxt = repo.next_match()
    if nxt and nxt.fecha:
        fecha = nxt.fecha
        if fecha.tzinfo is None:
            fecha = fecha.replace(tzinfo=timezone.utc)
        lead = timedelta(minutes=settings.sync_live_lead_minutes)
        if fecha - datetime.now(timezone.utc) <= lead:
            return ("inminente", settings.sync_live_seconds)

    return ("inactivo", max(60, settings.sync_interval_minutes * 60))


def _reschedule(seconds: int, mode: str) -> None:
    """Reprograma el job solo si cambió la cadencia."""
    global _current_seconds
    if _scheduler is None or seconds == _current_seconds:
        return
    _scheduler.reschedule_job(_JOB_ID, trigger="interval", seconds=seconds)
    _current_seconds = seconds
    logger.info("Sync reprogramado: modo=%s cada %ds", mode, seconds)


def sync_job() -> None:
    """Job periódico: sincroniza resultados y ajusta su propia cadencia."""
    db = SessionLocal()
    try:
        result = SyncService(db).sync()
        logger.info("Job de sincronización ejecutado: %s", result)
        mode, seconds = _decide_interval(db)
        _reschedule(seconds, mode)
    except Exception:  # noqa: BLE001 - el scheduler no debe morir por un fallo puntual
        logger.exception("Error en el job de sincronización")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Inicia el scheduler si la automatización está habilitada."""
    global _scheduler, _current_seconds
    if not settings.sync_enabled:
        logger.info("Automatización deshabilitada (SYNC_ENABLED=false)")
        return None
    if _scheduler and _scheduler.running:
        return _scheduler

    _current_seconds = max(60, settings.sync_interval_minutes * 60)
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        sync_job,
        trigger="interval",
        seconds=_current_seconds,
        id=_JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "Scheduler iniciado: intervalo inteligente (vivo=%ds, inactivo=%dm)",
        settings.sync_live_seconds,
        settings.sync_interval_minutes,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Detiene el scheduler de forma segura."""
    global _scheduler, _current_seconds
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")
    _scheduler = None
    _current_seconds = None
