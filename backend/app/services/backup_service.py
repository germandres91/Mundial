"""Respaldo y restauración de datos de usuarios y predicciones.

Exporta el estado actual (cuentas de acceso, participantes, predicciones de
partidos y pronósticos de los 4 puestos) a un JSON versionado en `data/`. Ese
archivo se restaura de forma idempotente en cada arranque, de modo que los
datos sobreviven a despliegues y mejoras de la aplicación.

Las referencias se guardan por claves estables (email del usuario/participante
y `fifa_id`/equipos del partido), no por IDs de base de datos, para que la
restauración funcione aunque la base se regenere desde cero.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import resolve_path, settings
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.models.user import UserRole
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.score_repository import ScoreRepository
from app.repositories.user_repository import UserRepository
from app.utils.teams import team_code

logger = get_logger(__name__)

BACKUP_VERSION = 2
DEFAULT_BACKUP_PATH = "data/backup.json"


class BackupService:
    """Crea y restaura respaldos del estado de usuarios y predicciones."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.participants = ParticipantRepository(db)
        self.predictions = PredictionRepository(db)
        self.positions = PositionPredictionRepository(db)
        self.matches = MatchRepository(db)
        self.scores = ScoreRepository(db)

    # ------------------------------------------------------------------ export
    def export_data(self) -> dict:
        """Serializa el estado actual a un diccionario."""
        participants = self.participants.list()
        part_email_by_id = {p.id: p.email for p in participants}
        matches = {m.id: m for m in self.matches.list()}

        users_out = []
        for u in self.users.list():
            users_out.append(
                {
                    "email": u.email,
                    "nombre": u.nombre,
                    "hashed_password": u.hashed_password,
                    "role": u.role.value,
                    "is_active": u.is_active,
                    "participant_email": part_email_by_id.get(u.participant_id),
                }
            )

        predictions_out = []
        locked_count = 0
        for pred in self.predictions.list():
            match = matches.get(pred.match_id)
            if match is None:
                continue
            if pred.locked_at is not None:
                locked_count += 1
            item = {
                "participant_email": part_email_by_id.get(pred.participant_id),
                "fifa_id": match.fifa_id,
                "local": match.local,
                "visitante": match.visitante,
                "pred_local": pred.pred_local,
                "pred_visitante": pred.pred_visitante,
            }
            if pred.locked_at is not None:
                item["locked_at"] = pred.locked_at.isoformat()
            predictions_out.append(item)

        positions_out = []
        for pos in self.positions.list_all():
            positions_out.append(
                {
                    "participant_email": part_email_by_id.get(pos.participant_id),
                    "posicion": pos.posicion,
                    "equipo": pos.equipo,
                }
            )

        match_results_out = []
        for m in self.matches.list():
            if (
                m.estado == MatchStatus.FINISHED
                and m.goles_local is not None
                and m.goles_visitante is not None
            ):
                match_results_out.append(
                    {
                        "fifa_id": m.fifa_id,
                        "local": m.local,
                        "visitante": m.visitante,
                        "goles_local": m.goles_local,
                        "goles_visitante": m.goles_visitante,
                        "goles_local_90": m.goles_local_90,
                        "goles_visitante_90": m.goles_visitante_90,
                        "penales_local": m.penales_local,
                        "penales_visitante": m.penales_visitante,
                        "ganador": m.ganador,
                        "estado": m.estado.value,
                        "fase": m.fase,
                    }
                )

        scores_out = []
        for score in self.scores.list():
            match = matches.get(score.match_id)
            if match is None:
                continue
            scores_out.append(
                {
                    "participant_email": part_email_by_id.get(score.participant_id),
                    "fifa_id": match.fifa_id,
                    "local": match.local,
                    "visitante": match.visitante,
                    "puntos": score.puntos,
                    "detalle": score.detalle,
                }
            )

        return {
            "version": BACKUP_VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "users": users_out,
            "participants": [{"nombre": p.nombre, "email": p.email} for p in participants],
            "predictions": predictions_out,
            "position_predictions": positions_out,
            "match_results": match_results_out,
            "scores": scores_out,
            "predicciones_bloqueadas": locked_count,
        }

    def write_backup(self, path: str | None = None) -> dict:
        """Genera el respaldo y lo escribe en disco. Devuelve un resumen."""
        data = self.export_data()
        target = resolve_path(path or DEFAULT_BACKUP_PATH)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        summary = {
            "ruta": str(target),
            "usuarios": len(data["users"]),
            "participantes": len(data["participants"]),
            "predicciones": len(data["predictions"]),
            "predicciones_bloqueadas": data.get("predicciones_bloqueadas", 0),
            "resultados_partidos": len(data.get("match_results", [])),
            "puntajes_guardados": len(data.get("scores", [])),
            "posiciones": len(data["position_predictions"]),
            "created_at": data["created_at"],
        }
        logger.info("Respaldo creado: %s", summary)
        return summary

    # ----------------------------------------------------------------- restore
    def _match_index(self) -> tuple[dict[str, object], dict[frozenset[str], object]]:
        by_fifa: dict[str, object] = {}
        by_codes: dict[frozenset[str], object] = {}
        for m in self.matches.list():
            if m.fifa_id:
                by_fifa[m.fifa_id] = m
            cl, cv = team_code(m.local), team_code(m.visitante)
            if cl and cv:
                by_codes[frozenset((cl, cv))] = m
        return by_fifa, by_codes

    def _participant_map(self) -> dict[str, object]:
        """Mapa email (minúsculas) -> participante."""
        return {p.email.lower(): p for p in self.participants.list()}

    def restore_data(self, data: dict) -> dict:
        """Restaura usuarios, participantes y predicciones de forma idempotente."""
        created_users = 0
        created_participants = 0
        restored_preds = 0
        restored_pos = 0

        # 1) Participantes (por email)
        for item in data.get("participants", []):
            email = str(item.get("email", "")).strip().lower()
            if not email:
                continue
            existing = self.participants.get_by_email(email)
            if existing is None:
                self.participants.create(
                    nombre=str(item.get("nombre", "")).strip() or email, email=email
                )
                created_participants += 1
        self.db.flush()

        part_by_email = self._participant_map()

        # 2) Usuarios de acceso (por email); preserva contraseñas existentes
        for item in data.get("users", []):
            email = str(item.get("email", "")).strip().lower()
            hashed = str(item.get("hashed_password", "")).strip()
            if not email or not hashed:
                continue
            part_email = item.get("participant_email")
            participant = None
            if part_email:
                participant = part_by_email.get(str(part_email).lower())
            if participant is None:
                # Enlaza por el mismo correo si no hay participant_email explícito
                participant = part_by_email.get(email)
            try:
                role = UserRole(item.get("role", "PARTICIPANT"))
            except ValueError:
                role = UserRole.PARTICIPANT
            existing = self.users.get_by_email(email)
            if existing is None:
                self.users.create(
                    email=email,
                    nombre=str(item.get("nombre", "")).strip() or email.split("@")[0],
                    hashed_password=hashed,
                    role=role,
                    participant_id=participant.id if participant else None,
                )
                created_users += 1
            else:
                if participant and existing.participant_id is None:
                    existing.participant_id = participant.id
                # No degradar al administrador principal si el respaldo trae otro rol.
                admin_email = settings.first_admin_email.lower()
                if email == admin_email and existing.role != UserRole.ADMIN:
                    existing.role = UserRole.ADMIN
        self.db.flush()

        # 3) Resultados oficiales de partidos (grupos + eliminatorias)
        by_fifa, by_codes = self._match_index()
        restored_results = 0
        for item in data.get("match_results", []):
            match = None
            fifa_id = item.get("fifa_id")
            if fifa_id and fifa_id in by_fifa:
                match = by_fifa[fifa_id]
            if match is None:
                cl, cv = team_code(item.get("local")), team_code(item.get("visitante"))
                if cl and cv:
                    match = by_codes.get(frozenset((cl, cv)))
            if match is None:
                continue
            match.goles_local = int(item.get("goles_local", 0))
            match.goles_visitante = int(item.get("goles_visitante", 0))
            if item.get("goles_local_90") is not None:
                match.goles_local_90 = int(item["goles_local_90"])
            if item.get("goles_visitante_90") is not None:
                match.goles_visitante_90 = int(item["goles_visitante_90"])
            elif match.goles_local_90 is None:
                match.goles_local_90 = match.goles_local
                match.goles_visitante_90 = match.goles_visitante
            if item.get("penales_local") is not None:
                match.penales_local = int(item["penales_local"])
            if item.get("penales_visitante") is not None:
                match.penales_visitante = int(item["penales_visitante"])
            if item.get("ganador"):
                match.ganador = str(item["ganador"])
            try:
                match.estado = MatchStatus(item.get("estado", MatchStatus.FINISHED.value))
            except ValueError:
                match.estado = MatchStatus.FINISHED
            restored_results += 1
        self.db.flush()

        # 4) Predicciones de partidos (upsert por participante + partido)
        skipped_preds = 0
        for item in data.get("predictions", []):
            participant = part_by_email.get(str(item.get("participant_email", "")).lower())
            if participant is None:
                skipped_preds += 1
                continue
            match = None
            fifa_id = item.get("fifa_id")
            if fifa_id and fifa_id in by_fifa:
                match = by_fifa[fifa_id]
            if match is None:
                cl, cv = team_code(item.get("local")), team_code(item.get("visitante"))
                if cl and cv:
                    match = by_codes.get(frozenset((cl, cv)))
            if match is None:
                skipped_preds += 1
                continue
            locked_at = None
            locked_raw = item.get("locked_at")
            if locked_raw:
                try:
                    locked_at = datetime.fromisoformat(str(locked_raw))
                except ValueError:
                    locked_at = None
            self.predictions.upsert(
                participant_id=participant.id,
                match_id=match.id,
                pred_local=int(item.get("pred_local", 0)),
                pred_visitante=int(item.get("pred_visitante", 0)),
                locked_at=locked_at,
            )
            restored_preds += 1

        if restored_preds == 0 and data.get("predictions"):
            logger.warning(
                "Respaldo: 0 predicciones restauradas de %d (¿falta el calendario oficial WC-A-*)",
                len(data["predictions"]),
            )
        elif skipped_preds:
            logger.info("Respaldo: %d predicciones omitidas (sin partido/participante)", skipped_preds)

        # 5) Pronósticos de puestos (puntos se recalculan aparte)
        for item in data.get("position_predictions", []):
            participant = part_by_email.get(str(item.get("participant_email", "")).lower())
            if participant is None:
                continue
            self.positions.upsert(
                participant_id=participant.id,
                posicion=int(item.get("posicion", 0)),
                equipo=str(item.get("equipo", "")).strip(),
                puntos=0,
            )
            restored_pos += 1

        # 6) Puntajes acumulados por partido (ranking histórico)
        restored_scores = 0
        skipped_scores = 0
        for item in data.get("scores", []):
            participant = part_by_email.get(str(item.get("participant_email", "")).lower())
            if participant is None:
                skipped_scores += 1
                continue
            match = None
            fifa_id = item.get("fifa_id")
            if fifa_id and fifa_id in by_fifa:
                match = by_fifa[fifa_id]
            if match is None:
                cl, cv = team_code(item.get("local")), team_code(item.get("visitante"))
                if cl and cv:
                    match = by_codes.get(frozenset((cl, cv)))
            if match is None:
                skipped_scores += 1
                continue
            self.scores.upsert(
                participant_id=participant.id,
                match_id=match.id,
                puntos=int(item.get("puntos", 0)),
                detalle=item.get("detalle"),
            )
            restored_scores += 1

        self.db.commit()
        summary = {
            "usuarios_creados": created_users,
            "participantes_creados": created_participants,
            "resultados_restaurados": restored_results,
            "predicciones_restauradas": restored_preds,
            "posiciones_restauradas": restored_pos,
            "puntajes_restaurados": restored_scores,
            "puntajes_omitidos": skipped_scores,
        }
        logger.info("Respaldo restaurado: %s", summary)
        return summary

    def restore_from_file(self, path: str | None = None) -> dict | None:
        """Restaura desde el archivo de respaldo si existe."""
        target = resolve_path(path or DEFAULT_BACKUP_PATH)
        if not target.exists():
            return None
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo leer el respaldo: %s", target)
            return None
        # Garantiza calendario oficial antes de enlazar predicciones/puntajes.
        from app.services.tournament_service import TournamentService

        TournamentService(self.db).seed_schedule()

        has_knockout = any(
            str(p.get("fifa_id") or "").startswith("KO-")
            for p in data.get("predictions", []) + data.get("scores", [])
        )
        if has_knockout:
            try:
                from app.services.knockout_service import KnockoutService

                KnockoutService(self.db).sync_r32_schedule()
            except Exception:  # noqa: BLE001
                logger.exception("No se pudieron crear partidos de eliminatorias al restaurar")

        return self.restore_data(data)
