"""Migración y recálculo de puntajes usando solo marcadores de 90 minutos."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import resolve_path
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.services.backup_service import DEFAULT_BACKUP_PATH, BackupService
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService
from app.utils.teams import team_code

logger = get_logger(__name__)

OVERRIDES_FILE = "data/match_90min_overrides.json"


class RegulationScoringService:
    """Backfill de marcadores a 90', correcciones y recálculo idempotente."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.matches = MatchRepository(db)
        self.backup = BackupService(db)

    def _load_overrides(self) -> dict[str, dict]:
        path = resolve_path(OVERRIDES_FILE)
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("partidos", {})

    def _timestamped_backup_path(self) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"data/backups/pre_90min_recalc_{stamp}.json"

    def create_safety_backup(self) -> dict:
        """Respaldo automático antes de tocar puntajes."""
        path = self._timestamped_backup_path()
        summary = self.backup.write_backup(path)
        # También actualiza el backup principal sin borrar predicciones.
        self.backup.write_backup(DEFAULT_BACKUP_PATH)
        summary["backup_seguridad"] = path
        return summary

    def backfill_regulation_scores(self) -> dict:
        """Completa goles_*_90 donde falten y aplica overrides oficiales."""
        overrides = self._load_overrides()
        by_fifa = {m.fifa_id: m for m in self.matches.list() if m.fifa_id}
        filled = 0
        overridden = 0

        for match in self.matches.list():
            if match.estado != MatchStatus.FINISHED:
                continue
            if match.goles_local is None or match.goles_visitante is None:
                continue
            if match.goles_local_90 is not None and match.goles_visitante_90 is not None:
                continue
            # En grupos, el marcador final coincide con los 90 minutos.
            if match.fase == "Fase de grupos":
                match.goles_local_90 = match.goles_local
                match.goles_visitante_90 = match.goles_visitante
                filled += 1

        for fifa_id, item in overrides.items():
            match = by_fifa.get(fifa_id)
            if match is None:
                cl, cv = team_code(item.get("local")), team_code(item.get("visitante"))
                if cl and cv:
                    for m in self.matches.list():
                        if {team_code(m.local), team_code(m.visitante)} == {cl, cv}:
                            match = m
                            break
            if match is None:
                logger.warning("Override sin partido en BD: %s", fifa_id)
                continue
            self._apply_override(match, item)
            overridden += 1

        self.db.flush()
        return {"rellenados_90": filled, "overrides_aplicados": overridden}

    @staticmethod
    def _apply_override(match, item: dict) -> None:
        for field in (
            "goles_local",
            "goles_visitante",
            "goles_local_90",
            "goles_visitante_90",
            "penales_local",
            "penales_visitante",
            "ganador",
        ):
            if field in item and item[field] is not None:
                setattr(match, field, item[field])
        match.estado = MatchStatus.FINISHED

    def recalculate_all(self, *, create_backup: bool = True, sync_first: bool = True) -> dict:
        """Flujo idempotente: backup → sync (opcional) → 90' → puntajes → ranking."""
        result: dict = {}
        if create_backup:
            result["backup"] = self.create_safety_backup()
        if sync_first:
            from app.services.sync_service import SyncService

            result["sync"] = SyncService(self.db).sync()
        result["backfill"] = self.backfill_regulation_scores()
        scored = ScoringService(self.db).recalculate_all()
        ranking = RankingService(self.db).recalculate()
        self.db.commit()
        result["partidos_repuntuados"] = scored
        result["ranking"] = ranking
        logger.info("Recálculo 90 minutos: %s", result)
        return result
