"""Inicialización de datos al arrancar la aplicación."""
from __future__ import annotations

from app.core.config import resolve_path
from app.core.database import SessionLocal, init_db
from app.core.logging import get_logger
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.services.auth_service import AuthService
from app.services.excel_service import ExcelService
from app.services.participant_import_service import ParticipantImportService
from app.services.ranking_service import RankingService
from app.services.tournament_service import TournamentService

logger = get_logger(__name__)


def bootstrap() -> None:
    """Crea tablas, reglas, calendario del torneo y carga el participante inicial."""
    init_db()
    db = SessionLocal()
    try:
        AuthService(db).ensure_first_admin()

        # Importa reglas (o siembra las por defecto)
        ExcelService(db).import_rules()

        # Crea el calendario del torneo (12 grupos, 72 partidos) si está vacío
        if MatchRepository(db).count() == 0:
            try:
                TournamentService(db).seed_schedule()
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo crear el calendario inicial")

        # Carga el participante inicial desde su formulario
        if not ParticipantRepository(db).list():
            formulario = resolve_path("data/formulario_german_bello.xlsm")
            if formulario.exists():
                try:
                    ParticipantImportService(db).import_formulario(
                        str(formulario),
                        nombre="German Andres Bello Garcia",
                        email="german.andres.bello.garcia@mundial2026.com",
                    )
                    RankingService(db).recalculate()
                except Exception:  # noqa: BLE001
                    logger.exception("No se pudo importar el formulario inicial")
    finally:
        db.close()
