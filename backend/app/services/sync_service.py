"""Servicio de sincronización con el proveedor de fútbol."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

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

# Prioridad para decidir qué estado "manda" al combinar lecturas del proveedor.
_STATUS_RANK = {
    MatchStatus.SCHEDULED: 0,
    MatchStatus.POSTPONED: 1,
    MatchStatus.CANCELLED: 1,
    MatchStatus.LIVE: 2,
    MatchStatus.FINISHED: 3,
}


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
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _resolve_status(cls, pm: ProviderMatch) -> MatchStatus:
        """Estado efectivo: API + ventana horaria si la API aún dice programado."""
        if pm.estado in (
            MatchStatus.LIVE,
            MatchStatus.FINISHED,
            MatchStatus.POSTPONED,
            MatchStatus.CANCELLED,
        ):
            return pm.estado
        if pm.fecha and pm.estado == MatchStatus.SCHEDULED:
            now = datetime.now(timezone.utc)
            kickoff = cls._as_utc(pm.fecha)
            # Ventana típica de un partido (90'+descanso+stoppage)
            if kickoff <= now < kickoff + timedelta(hours=2, minutes=15):
                return MatchStatus.LIVE
        return pm.estado

    def _mark_live_by_schedule(self) -> int:
        """Marca EN VIVO partidos programados cuya hora de inicio ya pasó."""
        now = datetime.now(timezone.utc)
        window = timedelta(hours=2, minutes=15)
        marked = 0
        for match in self.matches.list(estado=MatchStatus.SCHEDULED):
            if not match.fecha:
                continue
            kickoff = self._as_utc(match.fecha)
            if kickoff <= now < kickoff + window:
                match.estado = MatchStatus.LIVE
                marked += 1
        return marked

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
        match.estado = SyncService._resolve_status(pm)

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

    @staticmethod
    def _pm_key(pm: ProviderMatch) -> str:
        if pm.fifa_id:
            return f"id:{pm.fifa_id}"
        cl, cv = team_code(pm.local), team_code(pm.visitante)
        return f"teams:{'|'.join(sorted(filter(None, (cl, cv)))) or pm.local + pm.visitante}"

    @classmethod
    def _merge_pm(cls, base: ProviderMatch | None, new: ProviderMatch) -> ProviderMatch:
        """Combina dos lecturas del mismo partido conservando la más informativa.

        Mantiene cualquier marcador no nulo y el estado más avanzado observado
        (programado < en vivo < finalizado). Esto evita que una lectura "vacía"
        del tier gratuito borre un marcador real visto en otra lectura.
        """
        if base is None:
            return new
        if _STATUS_RANK.get(new.estado, 0) >= _STATUS_RANK.get(base.estado, 0):
            base.estado = new.estado
        if new.goles_local is not None:
            base.goles_local = new.goles_local
        if new.goles_visitante is not None:
            base.goles_visitante = new.goles_visitante
        base.fecha = new.fecha or base.fecha
        base.grupo = base.grupo or new.grupo
        base.fase = base.fase or new.fase
        return base

    def _should_be_live(self, pm: ProviderMatch) -> bool:
        if pm.estado == MatchStatus.FINISHED:
            return False
        if not pm.fecha:
            return False
        now = datetime.now(timezone.utc)
        kickoff = self._as_utc(pm.fecha)
        return kickoff <= now < kickoff + timedelta(hours=2, minutes=15)

    def _collect_provider_matches(
        self, attempts: int = 3, pause: float = 4.0
    ) -> list[ProviderMatch]:
        """Hace varias lecturas y las combina.

        El tier gratuito de football-data.org devuelve snapshots inconsistentes:
        una llamada puede traer el marcador en vivo y la siguiente darlo como
        programado sin goles. Combinamos hasta `attempts` lecturas para capturar
        de forma fiable el marcador de los partidos que están en juego.
        """
        merged: dict[str, ProviderMatch] = {}
        for i in range(max(1, attempts)):
            batch = self.provider.fetch_matches()
            for pm in batch:
                key = self._pm_key(pm)
                merged[key] = self._merge_pm(merged.get(key), pm)
            # ¿Hay algún partido que debería estar en vivo y aún sin marcador?
            pending = any(
                self._should_be_live(pm) and pm.goles_local is None
                for pm in merged.values()
            )
            if not pending or i == attempts - 1:
                break
            time.sleep(pause)
        return list(merged.values())

    def sync(self) -> dict[str, int]:
        """Ciclo completo: consulta API, actualiza, recalcula puntaje y ranking.

        Empareja cada partido de la API con uno propio (por id o por las dos
        selecciones). Si no encuentra correspondencia y `sync_create_missing`
        está desactivado, lo omite para no crear partidos ajenos al torneo.
        """
        provider_matches = self._collect_provider_matches()
        received = len(provider_matches)
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

        live_marked = self._mark_live_by_schedule()
        self.db.commit()

        # Recalcula el ranking si finalizó algún partido o si hay partidos en
        # vivo con marcador (para reflejar los puntos provisionales).
        live_with_score = any(
            m.goles_local is not None and m.goles_visitante is not None
            for m in self.matches.list(estado=MatchStatus.LIVE)
        )
        if newly_finished or live_with_score:
            RankingService(self.db).recalculate()

        self.audit.log(
            accion="SYNC",
            actor="scheduler",
            entidad="matches",
            detalle=(
                f"proveedor={self.provider.name}, recibidos={received}, "
                f"actualizados={updated}, finalizados={newly_finished}, "
                f"omitidos={skipped}, en_vivo_horario={live_marked}"
            ),
        )
        self.db.commit()
        result = {
            "recibidos": received,
            "actualizados": updated,
            "finalizados_nuevos": newly_finished,
            "omitidos": skipped,
            "en_vivo_horario": live_marked,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
        }
        logger.info("Sync completado: %s", result)
        return result
