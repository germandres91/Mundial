"""Servicio de sincronización con el proveedor de fútbol."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.match import Match, MatchStatus
from app.providers import BaseFootballProvider, ProviderMatch, get_provider
from app.repositories.audit_repository import AuditRepository
from app.repositories.match_repository import MatchRepository
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService
from app.utils.teams import team_code

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

    def _build_team_index(self) -> dict[frozenset[str], Match]:
        """Índice de partidos existentes por par de códigos de equipo."""
        index: dict[frozenset[str], Match] = {}
        for m in self.matches.list():
            cl, cv = team_code(m.local), team_code(m.visitante)
            if cl and cv:
                index[frozenset((cl, cv))] = m
        return index

    def _find_existing(
        self, pm: ProviderMatch, index: dict[frozenset[str], Match]
    ) -> Match | None:
        """Localiza el partido propio que corresponde al de la API.

        Primero por `fifa_id`; si no, empareja por el par de selecciones
        (independiente del idioma y del orden local/visitante).
        """
        if pm.fifa_id:
            match = self.matches.get_by_fifa_id(pm.fifa_id)
            if match:
                return match
        cl, cv = team_code(pm.local), team_code(pm.visitante)
        if cl and cv:
            return index.get(frozenset((cl, cv)))
        return None

    @staticmethod
    def _apply_result(match: Match, pm: ProviderMatch) -> None:
        """Vuelca el marcador/estado de la API en el partido propio.

        Ajusta la orientación si el equipo local de la API es el visitante
        nuestro (o viceversa).
        """
        gl, gv = pm.goles_local, pm.goles_visitante
        same_orientation = team_code(match.local) == team_code(pm.local)
        if not same_orientation:
            gl, gv = gv, gl
        if gl is not None:
            match.goles_local = gl
        if gv is not None:
            match.goles_visitante = gv
        if pm.fecha:
            match.fecha = pm.fecha
        match.estado = pm.estado

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
        """Ciclo completo: consulta API, actualiza, recalcula puntaje y ranking.

        Empareja cada partido de la API con uno propio (por id o por las dos
        selecciones). Si no encuentra correspondencia y `sync_create_missing`
        está desactivado, lo omite para no crear partidos ajenos al torneo.
        """
        provider_matches = self.provider.fetch_matches()
        newly_finished = 0
        updated = 0
        skipped = 0

        index = self._build_team_index()
        scoring = ScoringService(self.db)
        for pm in provider_matches:
            match = self._find_existing(pm, index)
            if match is None:
                if not settings.sync_create_missing:
                    skipped += 1
                    continue
                was_finished = False
                match = self._upsert_match(pm)
                cl, cv = team_code(match.local), team_code(match.visitante)
                if cl and cv:
                    index[frozenset((cl, cv))] = match
            else:
                was_finished = match.estado == MatchStatus.FINISHED
                self._apply_result(match, pm)

            updated += 1
            if match.estado == MatchStatus.FINISHED and match.goles_local is not None:
                self.db.flush()
                scoring.score_match(match)
                if not was_finished:
                    newly_finished += 1

        self.db.commit()

        if newly_finished:
            RankingService(self.db).recalculate()

        self.audit.log(
            accion="SYNC",
            actor="scheduler",
            entidad="matches",
            detalle=(
                f"proveedor={self.provider.name}, actualizados={updated}, "
                f"finalizados={newly_finished}, omitidos={skipped}"
            ),
        )
        self.db.commit()
        result = {
            "actualizados": updated,
            "finalizados_nuevos": newly_finished,
            "omitidos": skipped,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        logger.info("Sync completado: %s", result)
        return result
