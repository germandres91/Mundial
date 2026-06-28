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



logger = get_logger(__name__)



FASE_R32 = "Dieciseisavos de final"

FASE_R16 = "Octavos de final"

FASE_QF = "Cuartos de final"

FASE_SF = "Semifinales"

FASE_FINAL = "Final"



KNOCKOUT_FASES = (FASE_R32, FASE_R16, FASE_QF, FASE_SF, FASE_FINAL)



R32_DATA_FILE = "data/knockout_r32_2026.json"





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



    def advance_next_round(self, from_fase: str) -> dict:

        """Avanza a la siguiente ronda cuando todos los partidos de ``from_fase`` terminaron."""

        chain = {

            FASE_R32: (FASE_R16, "KO-R16", 8),

            FASE_R16: (FASE_QF, "KO-QF", 4),

            FASE_QF: (FASE_SF, "KO-SF", 2),

            FASE_SF: (FASE_FINAL, "KO-F", 1),

        }

        if from_fase not in chain:

            raise ValueError(f"Fase no soportada: {from_fase}")



        current = self.matches.list(fase=from_fase)

        if not current:

            raise ValueError(f"No hay partidos en {from_fase}")

        unfinished = [m for m in current if m.estado != MatchStatus.FINISHED]

        if unfinished:

            raise ValueError(

                f"Quedan {len(unfinished)} partidos sin finalizar en {from_fase}"

            )



        next_fase, prefix, count = chain[from_fase]

        if self.matches.list(fase=next_fase):

            return {"created": 0, "message": f"{next_fase} ya existe"}



        winners: list[str] = []

        for m in sorted(current, key=lambda x: x.fifa_id or ""):

            if m.goles_local is None or m.goles_visitante is None:

                raise ValueError(f"Partido sin marcador: {m.fifa_id}")

            winners.append(m.local if m.goles_local > m.goles_visitante else m.visitante)



        base = datetime.now(timezone.utc) + timedelta(days=2)

        created = 0

        for i in range(0, len(winners), 2):

            if i + 1 >= len(winners):

                break

            n = i // 2 + 1

            fifa_id = f"{prefix}-{n}"

            self.matches.create(

                fifa_id=fifa_id,

                grupo=None,

                fase=next_fase,

                local=winners[i],

                visitante=winners[i + 1],

                fecha=base + timedelta(hours=4 * n),

                estado=MatchStatus.SCHEDULED,

            )

            created += 1



        self.db.commit()

        return {"created": created, "fase": next_fase, "from_fase": from_fase}



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

        return out





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


def r32_display_by_fifa_id() -> dict[str, dict]:
    """Metadata de calendario Colombia por partido de dieciseisavos."""
    try:
        fixtures = load_r32_fixtures().get("partidos", [])
    except ValueError:
        return {}
    return {
        fx["fifa_id"]: {
            "match_no": fx.get("match_no"),
            "hora_colombia": fx.get("hora_colombia"),
            "fecha_dia_colombia": fx.get("fecha_dia_colombia"),
        }
        for fx in fixtures
    }


