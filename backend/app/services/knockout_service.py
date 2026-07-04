"""Generación de partidos de eliminatorias a partir del cuadro oficial."""

from __future__ import annotations



import json

from datetime import date, datetime, timedelta, timezone



from sqlalchemy.orm import Session



from app.core.config import resolve_path

from app.core.logging import get_logger

from app.models.match import MatchStatus

from app.repositories.match_repository import MatchRepository

from app.services.tournament_service import TournamentService

from app.utils.bracket_paths import (
    knockout_slot_sort_key,
    pair_winners_r32_to_r16,
    pair_winners_sequential,
)



logger = get_logger(__name__)



FASE_R32 = "Dieciseisavos de final"

FASE_R16 = "Octavos de final"

FASE_QF = "Cuartos de final"

FASE_SF = "Semifinales"

FASE_FINAL = "Final"



KNOCKOUT_FASES = (FASE_R32, FASE_R16, FASE_QF, FASE_SF, FASE_FINAL)



R32_DATA_FILE = "data/knockout_r32_2026.json"
KO_ROUNDS_FILE = "data/knockout_ko_rounds.json"





def seed_order(n: int) -> list[int]:

    """Orden de siembra estándar para cuadro de n equipos (misma lógica que Bracket.jsx)."""

    arr = [1, 2]

    while len(arr) < n:

        length = len(arr) * 2

        nxt: list[int] = []

        for s in arr:

            nxt.append(s)

            nxt.append(length + 1 - s)

        arr = nxt

    return arr





def load_r32_fixtures() -> dict:

    """Cuadro oficial de dieciseisavos (cruces + horarios UTC)."""

    path = resolve_path(R32_DATA_FILE)

    if not path.exists():

        raise ValueError(f"No se encontró {R32_DATA_FILE}")

    data = json.loads(path.read_text(encoding="utf-8"))

    return data


def load_ko_rounds_data() -> dict:
    path = resolve_path(KO_ROUNDS_FILE)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def round_schedule_by_fifa_id(fase: str) -> dict[str, dict]:
    block = load_ko_rounds_data().get(fase) or {}
    return {fx["fifa_id"]: fx for fx in block.get("partidos", []) if fx.get("fifa_id")}


def parse_fixture_fecha(raw: str) -> datetime:

    return datetime.fromisoformat(raw)





class KnockoutService:

    def __init__(self, db: Session) -> None:

        self.db = db

        self.matches = MatchRepository(db)

        self.tournament = TournamentService(db)



    def _qualified_teams(self) -> list[dict]:

        standings = self.tournament._standings_from(None)

        qualified = self.tournament._qualified_from(standings)

        if len(qualified) < 32:

            raise ValueError(

                f"Faltan resultados de grupos: solo hay {len(qualified)} clasificados "

                "(se necesitan 32). Verifica que los 72 partidos de grupos estén finalizados."

            )

        return qualified[:32]



    def sync_r32_schedule(self) -> dict:

        """Crea o actualiza los 16 partidos con cruces y horarios oficiales."""

        data = load_r32_fixtures()

        fase = data.get("fase", FASE_R32)

        created = 0

        updated = 0

        fixtures = data.get("partidos", [])



        for fx in fixtures:

            fifa_id = fx["fifa_id"]

            fecha = parse_fixture_fecha(fx["fecha_utc"])

            existing = self.matches.get_by_fifa_id(fifa_id)

            if existing:

                if existing.estado == MatchStatus.FINISHED:

                    continue

                changed = False

                if existing.local != fx["local"]:

                    existing.local = fx["local"]

                    changed = True

                if existing.visitante != fx["visitante"]:

                    existing.visitante = fx["visitante"]

                    changed = True

                if existing.fecha != fecha:

                    existing.fecha = fecha

                    changed = True

                if existing.fase != fase:

                    existing.fase = fase

                    changed = True

                if changed:

                    updated += 1

                continue



            self.matches.create(

                fifa_id=fifa_id,

                grupo=None,

                fase=fase,

                local=fx["local"],

                visitante=fx["visitante"],

                fecha=fecha,

                estado=MatchStatus.SCHEDULED,

            )

            created += 1



        self.db.commit()

        total = len(

            [

                m

                for m in self.matches.list(fase=fase)

                if m.fifa_id and m.fifa_id.startswith("KO-R32-")

            ]

        )

        logger.info("Dieciseisavos sincronizados: %d creados, %d actualizados", created, updated)

        return {

            "created": created,

            "updated": updated,

            "total": total,

            "fase": fase,

            "partidos": [

                {

                    "fifa_id": fx["fifa_id"],

                    "local": fx["local"],

                    "visitante": fx["visitante"],

                    "fecha": fx["fecha_utc"],

                    "hora_colombia": fx.get("hora_colombia"),

                }

                for fx in fixtures

            ],

        }



    def advance_round_of_32(self) -> dict:

        """Publica los dieciseisavos con el cuadro oficial FIFA (post fase de grupos)."""

        result = self.sync_r32_schedule()

        if result["created"] == 0 and result["updated"] == 0:

            result["message"] = "Los dieciseisavos ya estaban al día"

        return result

    def sync_internet_results(self) -> dict:
        """Consulta ESPN/API, aplica overrides de 90' y confirma ganadores."""
        from app.services.regulation_scoring_service import RegulationScoringService
        from app.services.sync_service import SyncService

        sync = SyncService(self.db).sync()
        backfill = RegulationScoringService(self.db).backfill_regulation_scores()
        self.db.commit()
        return {"sync": sync, "backfill": backfill}

    @staticmethod
    def _find_provider_match(provider_matches, local: str, visitante: str):
        from app.utils.teams import team_code

        cl, cv = team_code(local), team_code(visitante)
        if not cl or not cv:
            return None
        target = frozenset((cl, cv))
        for pm in provider_matches:
            pm_set = frozenset(filter(None, (team_code(pm.local), team_code(pm.visitante))))
            if pm_set == target:
                return pm
        return None

    def advance_next_round(self, from_fase: str, *, sync_internet: bool = True) -> dict:
        """Avanza a la siguiente ronda cuando la fase indicada terminó."""
        sync_info = self.sync_internet_results() if sync_internet else None

        chain = {
            FASE_R32: (FASE_R16, "KO-R16", 8),
            FASE_R16: (FASE_QF, "KO-QF", 4),
            FASE_QF: (FASE_SF, "KO-SF", 2),
            FASE_SF: (FASE_FINAL, "KO-F", 1),
        }
        if from_fase not in chain:
            raise ValueError(f"Fase no soportada: {from_fase}")

        current = sorted(
            self.matches.list(fase=from_fase),
            key=lambda x: knockout_slot_sort_key(x.fifa_id),
        )
        if not current:
            hints = {
                FASE_R16: " Genera primero los octavos con «Publicar octavos» (desde dieciseisavos).",
                FASE_QF: " Genera primero los cuartos desde octavos.",
                FASE_SF: " Genera primero las semifinales desde cuartos.",
            }
            raise ValueError(f"No hay partidos en {from_fase}.{hints.get(from_fase, '')}")

        unfinished = [m for m in current if m.estado != MatchStatus.FINISHED]
        if unfinished:
            sample = ", ".join(
                f"{m.fifa_id} ({m.local} vs {m.visitante})" for m in unfinished[:4]
            )
            extra = f" y {len(unfinished) - 4} más" if len(unfinished) > 4 else ""
            raise ValueError(
                f"Quedan {len(unfinished)} partidos sin finalizar en {from_fase}: "
                f"{sample}{extra}. Sincroniza resultados desde internet e intenta de nuevo."
            )

        without_winner = [m for m in current if not m.classified_winner()]
        if without_winner:
            sample = ", ".join(
                f"{m.fifa_id} ({m.local} vs {m.visitante})" for m in without_winner[:4]
            )
            raise ValueError(
                f"Faltan ganadores clasificados en {from_fase}: {sample}. "
                "Verifica penales/ganador o sincroniza desde internet."
            )

        next_fase, prefix, _count = chain[from_fase]
        existing_next = self.matches.list(fase=next_fase)
        if existing_next:
            return {
                "created": 0,
                "message": f"{next_fase} ya existe ({len(existing_next)} partidos)",
                "sync": sync_info,
            }

        if from_fase == FASE_R32:
            try:
                pairs = pair_winners_r32_to_r16(current, lambda m: m.classified_winner())
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
        else:
            winners: list[str] = []
            for m in current:
                winner = m.classified_winner()
                if winner is None:
                    raise ValueError(f"Partido sin ganador clasificado: {m.fifa_id}")
                winners.append(winner)
            pairs = pair_winners_sequential(winners)

        schedule = round_schedule_by_fifa_id(next_fase)
        provider_matches = []
        if sync_internet:
            from app.providers import get_provider

            provider_matches = get_provider().fetch_matches()

        base = datetime.now(timezone.utc) + timedelta(days=2)
        created = 0
        partidos: list[dict] = []

        for i, (local, visitante) in enumerate(pairs, start=1):
            fifa_id = f"{prefix}-{i}"
            fx = schedule.get(fifa_id, {})
            if fx.get("fecha_utc"):
                fecha = parse_fixture_fecha(fx["fecha_utc"])
            else:
                fecha = base + timedelta(hours=4 * i)

            pm = self._find_provider_match(provider_matches, local, visitante)
            if pm and pm.fecha:
                fecha = pm.fecha

            self.matches.create(
                fifa_id=fifa_id,
                grupo=None,
                fase=next_fase,
                local=local,
                visitante=visitante,
                fecha=fecha,
                estado=MatchStatus.SCHEDULED,
            )
            created += 1
            partidos.append(
                {
                    "fifa_id": fifa_id,
                    "local": local,
                    "visitante": visitante,
                    "fecha": fecha.isoformat(),
                    "hora_colombia": fx.get("hora_colombia"),
                }
            )

        self.db.commit()
        return {
            "created": created,
            "fase": next_fase,
            "from_fase": from_fase,
            "sync": sync_info,
            "partidos": partidos,
        }

    def status(self) -> dict:
        """Resumen de fases eliminatorias."""
        out = {}
        for fase in KNOCKOUT_FASES:
            ms = self.matches.list(fase=fase)
            out[fase] = {
                "total": len(ms),
                "finished": sum(1 for m in ms if m.estado == MatchStatus.FINISHED),
                "scheduled": sum(1 for m in ms if m.estado == MatchStatus.SCHEDULED),
            }
        try:
            fixtures = load_r32_fixtures().get("partidos", [])
            out["r32_oficial_disponible"] = len(fixtures)
        except ValueError:
            out["r32_oficial_disponible"] = 0
        ko_data = load_ko_rounds_data()
        out["ko_calendario_disponible"] = sum(
            len((ko_data.get(f) or {}).get("partidos", []))
            for f in (FASE_R16, FASE_QF, FASE_SF, FASE_FINAL)
        )
        return out


def r32_late_submit_allowed() -> set[str]:
    """Partidos que aceptan envío tardío (pendiente de aprobación) aunque ya empezaron."""
    try:
        raw = load_r32_fixtures().get("late_submit_allowed", [])
    except ValueError:
        return set()
    return {str(x) for x in raw}


def r32_grace_submit_days() -> dict[str, date]:

    """Partidos que aceptan predicción todo el día indicado (zona Colombia)."""

    try:

        raw = load_r32_fixtures().get("grace_submit_day", {})

    except ValueError:

        return {}

    out: dict[str, date] = {}

    for fifa_id, day in raw.items():

        out[fifa_id] = date.fromisoformat(day)

    return out


def knockout_display_by_fifa_id() -> dict[str, dict]:
    """Metadata de calendario Colombia por partido eliminatorio (R32 → final)."""
    out: dict[str, dict] = {}
    try:
        for fx in load_r32_fixtures().get("partidos", []):
            fid = fx.get("fifa_id")
            if fid:
                out[fid] = {
                    "match_no": fx.get("match_no"),
                    "hora_colombia": fx.get("hora_colombia"),
                    "fecha_dia_colombia": fx.get("fecha_dia_colombia"),
                }
    except ValueError:
        pass
    for fase in (FASE_R16, FASE_QF, FASE_SF, FASE_FINAL):
        for fx in (load_ko_rounds_data().get(fase) or {}).get("partidos", []):
            fid = fx.get("fifa_id")
            if fid:
                out[fid] = {
                    "match_no": fx.get("match_no"),
                    "hora_colombia": fx.get("hora_colombia"),
                    "fecha_dia_colombia": fx.get("fecha_dia_colombia"),
                }
    return out


def r32_display_by_fifa_id() -> dict[str, dict]:
    """Alias retrocompatible."""
    return knockout_display_by_fifa_id()


