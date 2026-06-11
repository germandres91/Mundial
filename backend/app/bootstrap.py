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
from app.services.scoring_service import ScoringService
from app.services.tournament_service import TournamentService

logger = get_logger(__name__)


def bootstrap() -> None:
    """Inicializa la app sin tumbar el arranque ante cualquier error.

    Cada paso está aislado: si uno falla (p. ej. en Azure con BD nueva o un
    archivo ausente), se registra el error y la API igualmente queda en línea.
    """
    try:
        init_db()
    except Exception:  # noqa: BLE001
        logger.exception("Fallo al inicializar la base de datos")
        return

    db = SessionLocal()
    try:
        try:
            AuthService(db).ensure_first_admin()
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo asegurar el administrador inicial")

        try:
            ExcelService(db).import_rules()
        except Exception:  # noqa: BLE001
            logger.exception("No se pudieron importar las reglas")

        # Crea el calendario del torneo (12 grupos, 72 partidos) si está vacío
        try:
            if MatchRepository(db).count() == 0:
                TournamentService(db).seed_schedule()
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo crear el calendario inicial")

        # Carga el participante inicial desde su formulario
        try:
            if not ParticipantRepository(db).list():
                formulario = resolve_path("data/formulario_german_bello.xlsm")
                if formulario.exists():
                    ParticipantImportService(db).import_formulario(
                        str(formulario),
                        nombre="German Andres Bello Garcia",
                        email="german.andres.bello.garcia@mundial2026.com",
                    )
                    RankingService(db).recalculate()
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo importar el formulario inicial")

        # Normaliza el bonus de posiciones según el resultado real vigente.
        # Corrige datos antiguos que pudieran tener puntos preasignados.
        try:
            ScoringService(db).score_positions()
            db.commit()
            RankingService(db).recalculate()
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo normalizar el bonus de posiciones")
    finally:
        db.close()
