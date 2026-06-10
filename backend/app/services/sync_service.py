"""Servicio de sincronización con el proveedor de fútbol."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.providers import BaseFootballProvider, ProviderMatch, get_provider
from app.repositories.audit_repository import AuditRepository
from app.repositories.match_repository import MatchRepository
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService

logger = get_logger(__name__)


class SyncService:
    """Trae partidos del proveedor, actualiza resultados y recalcula puntajes."""

    def __init__(self, db: Session, provider: BaseFootballProvider | None = None) -> None:
        self.db = db
        self.provider = provider or get_provider()
        self.matches = MatchRepository(db)
        self.audit = AuditRepository(db)

    def import_calendar(self) -> int:
        """Crea/actualiza la estructura de partidos a partir del proveedor."""
        provider_matches = self.provider.fetch_matches()
        upserted = 0
        for pm in provider_matches:
            self._upsert_match(pm)
            upserted += 1
        self.db.commit()
        logger.info("Calendario importado: %d partidos", upserted)
        return upserted

    def _upsert_match(self, pm: ProviderMatch):
        match = self.matches.get_by_fifa_id(pm.fifa_id) if pm.fifa_id else None
        if match is None:
            return self.matches.create(
                fifa_id=pm.fifa_id,
                grupo=pm.grupo,
                fase=pm.fase,
                local=pm.local,
                visitante=pm.visitante,
                fecha=pm.fecha,
                goles_local=pm.goles_local,
                goles_visitante=pm.goles_visitante,
                estado=pm.estado,
            )
        match.grupo = pm.grupo or match.grupo
        match.fase = pm.fase or match.fase
        match.fecha = pm.fecha or match.fecha
        if pm.goles_local is not None:
            match.goles_local = pm.goles_local
        if pm.goles_visitante is not None:
            match.goles_visitante = pm.goles_visitante
        match.estado = pm.estado
        return match

    def sync(self) -> dict[str, int]:
        """Ciclo completo: consulta API, actualiza, recalcula puntaje y ranking."""
        provider_matches = self.provider.fetch_matches()
        newly_finished = 0
        updated = 0

        scoring = ScoringService(self.db)
        for pm in provider_matches:
            if not pm.fifa_id:
                continue
            match = self.matches.get_by_fifa_id(pm.fifa_id)
            was_finished = bool(match and match.estado == MatchStatus.FINISHED)
            match = self._upsert_match(pm)
            updated += 1
            if match.estado == MatchStatus.FINISHED and not was_finished:
                self.db.flush()
                scoring.score_match(match)
                newly_finished += 1

        self.db.commit()

        if newly_finished:
            RankingService(self.db).recalculate()

        self.audit.log(
            accion="SYNC",
            actor="scheduler",
            entidad="matches",
            detalle=f"actualizados={updated}, finalizados_nuevos={newly_finished}",
        )
        self.db.commit()
        result = {
            "actualizados": updated,
            "finalizados_nuevos": newly_finished,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        logger.info("Sync completado: %s", result)
        return result
