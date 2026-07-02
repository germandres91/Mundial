"""Servicio del torneo: calendario, tabla de posiciones y bracket eliminatorio."""
from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.config import resolve_path
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.repositories.prediction_repository import PredictionRepository

logger = get_logger(__name__)


def _empty_row(equipo: str) -> dict:
    return {
        "equipo": equipo,
        "pj": 0, "pg": 0, "pe": 0, "pp": 0,
        "gf": 0, "gc": 0, "dg": 0, "pts": 0,
    }


def _apply(row_l: dict, row_v: dict, gl: int, gv: int) -> None:
    row_l["pj"] += 1
    row_v["pj"] += 1
    row_l["gf"] += gl
    row_l["gc"] += gv
    row_v["gf"] += gv
    row_v["gc"] += gl
    if gl > gv:
        row_l["pg"] += 1
        row_l["pts"] += 3
        row_v["pp"] += 1
    elif gl < gv:
        row_v["pg"] += 1
        row_v["pts"] += 3
        row_l["pp"] += 1
    else:
        row_l["pe"] += 1
        row_v["pe"] += 1
        row_l["pts"] += 1
        row_v["pts"] += 1
    for r in (row_l, row_v):
        r["dg"] = r["gf"] - r["gc"]


def _sort_table(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r["pts"], r["dg"], r["gf"]), reverse=True)


class TournamentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.matches = MatchRepository(db)
        self.predictions = PredictionRepository(db)
        self.participants = ParticipantRepository(db)
        self.positions = PositionPredictionRepository(db)

    # --------------------------- Calendario ---------------------------
    def seed_schedule(self) -> int:
        """Crea los partidos del torneo desde data/tournament_2026.json si faltan."""
        path = resolve_path("data/tournament_2026.json")
        if not path.exists():
            logger.warning("tournament_2026.json no encontrado en %s", path)
            return 0
        data = json.loads(path.read_text(encoding="utf-8"))
        created = 0
        from datetime import datetime, timedelta, timezone

        base = datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc)
        idx = 0
        for grupo in data.get("grupos", []):
            for partido in grupo.get("partidos", []):
                idx += 1
                if self.matches.get_by_fifa_id(partido["fifa_id"]):
                    continue
                self.matches.create(
                    fifa_id=partido["fifa_id"],
                    grupo=grupo["grupo"],
                    fase="Fase de grupos",
                    local=partido["local"],
                    visitante=partido["visitante"],
                    fecha=base + timedelta(hours=4 * idx),
                    estado=MatchStatus.SCHEDULED,
                )
                created += 1
        self.db.commit()
        logger.info("Calendario sembrado: %d partidos nuevos", created)
        return created

    # ------------------------ Tabla de posiciones ------------------------
    def _standings_from(self, use_predictions_of: int | None) -> dict[str, list[dict]]:
        """Calcula posiciones por grupo. Si se indica un participante, usa sus
        predicciones; de lo contrario, usa los resultados reales finalizados."""
        all_matches = [m for m in self.matches.list() if m.fase == "Fase de grupos"]
        tables: dict[str, dict[str, dict]] = defaultdict(dict)

        # Inicializa filas con todos los equipos del grupo
        for m in all_matches:
            grp = tables[m.grupo or "?"]
            grp.setdefault(m.local, _empty_row(m.local))
            grp.setdefault(m.visitante, _empty_row(m.visitante))

        pred_map: dict[int, tuple[int, int]] = {}
        if use_predictions_of is not None:
            for p in self.predictions.list(participant_id=use_predictions_of):
                pred_map[p.match_id] = (p.pred_local, p.pred_visitante)

        for m in all_matches:
            grp = tables[m.grupo or "?"]
            if use_predictions_of is not None:
                if m.id not in pred_map:
                    continue
                gl, gv = pred_map[m.id]
            else:
                if m.estado != MatchStatus.FINISHED or m.goles_local is None:
                    continue
                gl, gv = m.goles_local, m.goles_visitante
            _apply(grp[m.local], grp[m.visitante], gl, gv)

        return {grupo: _sort_table(list(rows.values())) for grupo, rows in tables.items()}

    # ------------------------- Clasificados -------------------------
    def _qualified_from(self, source: dict[str, list[dict]]) -> list[dict]:
        """Lista de clasificados a eliminatorias (formato Mundial 2026):
        12 primeros + 12 segundos + 8 mejores terceros, ordenados por siembra."""
        winners: list[dict] = []
        runners: list[dict] = []
        thirds: list[dict] = []
        for grupo in sorted(source.keys()):
            tabla = source[grupo]
            if len(tabla) >= 1:
                winners.append({**tabla[0], "grupo": grupo, "posicion": 1})
            if len(tabla) >= 2:
                runners.append({**tabla[1], "grupo": grupo, "posicion": 2})
            if len(tabla) >= 3:
                thirds.append({**tabla[2], "grupo": grupo, "posicion": 3})

        best_thirds = sorted(
            thirds, key=lambda r: (r["pts"], r["dg"], r["gf"]), reverse=True
        )[:8]

        pool = winners + runners + best_thirds
        # Siembra: primero por posición de grupo (1 mejor), luego por rendimiento
        ranked = sorted(pool, key=lambda r: (r["posicion"], -r["pts"], -r["dg"], -r["gf"]))
        return [
            {
                "equipo": r["equipo"],
                "grupo": r["grupo"],
                "posicion": r["posicion"],
                "pts": r["pts"],
                "dg": r["dg"],
                "gf": r["gf"],
                "rank": i,
            }
            for i, r in enumerate(ranked, start=1)
        ]

    # ----------------------------- Bracket -----------------------------
    def bracket(self, participant_id: int | None = None) -> dict:
        real = self._standings_from(None)
        predicted = (
            self._standings_from(participant_id) if participant_id is not None else None
        )

        grupos = []
        for grupo in sorted(real.keys()):
            entry = {"grupo": grupo, "posiciones": real[grupo]}
            if predicted is not None:
                entry["pronostico"] = predicted.get(grupo, [])
            grupos.append(entry)

        # Clasificados (top 2) según la fuente disponible
        source = predicted if predicted is not None else real
        clasificados = []
        for grupo in sorted(source.keys()):
            tabla = source[grupo]
            for i, row in enumerate(tabla[:2]):
                clasificados.append(
                    {"grupo": grupo, "puesto": i + 1, "equipo": row["equipo"]}
                )

        # Top-4 pronosticado del participante
        top4 = []
        if participant_id is not None:
            for pos in self.positions.list_for(participant_id):
                top4.append(
                    {"posicion": pos.posicion, "equipo": pos.equipo, "puntos": pos.puntos}
                )
            top4.sort(key=lambda x: x["posicion"])

        # Partidos de eliminatorias (si existieran en la BD)
        knockout = [
            {
                "id": m.id,
                "fifa_id": m.fifa_id,
                "fase": m.fase,
                "local": m.local,
                "visitante": m.visitante,
                "goles_local": m.goles_local,
                "goles_visitante": m.goles_visitante,
                "goles_local_90": m.goles_local_90,
                "goles_visitante_90": m.goles_visitante_90,
                "ganador": m.ganador,
                "estado": m.estado.value,
                "minuto": m.minuto,
                "fecha": m.fecha.isoformat() if m.fecha else None,
            }
            for m in self.matches.list()
            if m.fase and m.fase != "Fase de grupos"
        ]

        return {
            "grupos": grupos,
            "clasificados": clasificados,
            "qualified": self._qualified_from(source),
            "top4": top4,
            "knockout": knockout,
            "fuente": "pronostico" if predicted is not None else "real",
        }
