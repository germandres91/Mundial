"""Generación de partidos de eliminatorias a partir del cuadro oficial."""

from __future__ import annotations



import json

from datetime import date, datetime, timedelta, timezone



from sqlalchemy import select
from sqlalchemy.orm import Session



from app.core.config import resolve_path

from app.core.logging import get_logger

from app.models.match import MatchStatus

from app.repositories.match_repository import MatchRepository

from app.services.tournament_service import TournamentService

from app.utils.bracket_paths import (
    knockout_slot_sort_key,
    pair_losers_sf_to_third,
    pair_winners_qf_to_sf,
    pair_winners_r16_to_qf,
    pair_winners_r32_to_r16,
    pair_winners_sf_to_final,
)



logger = get_logger(__name__)



FASE_R32 = "Dieciseisavos de final"

FASE_R16 = "Octavos de final"

FASE_QF = "Cuartos de final"

FASE_SF = "Semifinales"

FASE_3RD = "Tercer puesto"

FASE_FINAL = "Final"



KNOCKOUT_FASES = (FASE_R32, FASE_R16, FASE_QF, FASE_SF, FASE_3RD, FASE_FINAL)



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
        try:
            pairs = self._pairs_for_advance(from_fase, current)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        provider_matches = []
        if sync_internet:
            from app.providers import get_provider

            provider_matches = get_provider().fetch_matches()

        rounds_to_write: list[tuple[str, str, list[tuple[str, str]]]] = [
            (next_fase, prefix, pairs)
        ]
        if from_fase == FASE_SF:
            try:
                third_pairs = pair_losers_sf_to_third(
                    current, lambda m: m.classified_loser()
                )
            except ValueError as exc:
                raise ValueError(str(exc)) from exc
            # Tercer puesto (Match 103) antes que la Final (Match 104).
            rounds_to_write = [
                (FASE_3RD, "KO-3RD", third_pairs),
                (FASE_FINAL, "KO-F", pairs),
            ]

        created = 0
        updated = 0
        partidos: list[dict] = []
        fases_creadas: list[str] = []

        for fase_name, id_prefix, fase_pairs in rounds_to_write:
            stats = self._upsert_round_matches(
                fase=fase_name,
                prefix=id_prefix,
                pairs=fase_pairs,
                provider_matches=provider_matches,
            )
            created += stats["created"]
            updated += stats["updated"]
            partidos.extend(stats["partidos"])
            if stats["created"] or stats["updated"] or stats["partidos"]:
                fases_creadas.append(fase_name)

        self.db.commit()

        if from_fase == FASE_SF:
            if created == 0 and updated == 0:
                message = "Final y tercer puesto ya existen y están al día"
            elif updated and not created:
                message = (
                    f"Final / tercer puesto: {updated} partidos corregidos al cuadro FIFA"
                )
            else:
                message = None
            fase_label = " / ".join(fases_creadas) if fases_creadas else FASE_FINAL
        elif created == 0 and updated == 0:
            existing_count = len(self.matches.list(fase=next_fase))
            message = (
                f"{next_fase} ya existe ({existing_count} partidos) y está al día"
                if existing_count
                else None
            )
            fase_label = next_fase
        elif updated and not created:
            message = f"{next_fase}: {updated} partidos corregidos al cuadro FIFA"
            fase_label = next_fase
        else:
            message = None
            fase_label = next_fase

        return {
            "created": created,
            "updated": updated,
            "fase": fase_label,
            "from_fase": from_fase,
            "sync": sync_info,
            "partidos": partidos,
            "message": message,
        }

    def _upsert_round_matches(
        self,
        *,
        fase: str,
        prefix: str,
        pairs: list[tuple[str, str]],
        provider_matches: list,
    ) -> dict:
        schedule = round_schedule_by_fifa_id(fase)
        base = datetime.now(timezone.utc) + timedelta(days=2)
        created = 0
        updated = 0
        partidos: list[dict] = []
        existing_by_fifa = {
            m.fifa_id: m for m in self.matches.list(fase=fase) if m.fifa_id
        }

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

            existing = existing_by_fifa.get(fifa_id)
            if existing is None:
                # También busca por fifa_id global (p. ej. Final ya creada sin 3er puesto).
                existing = self.matches.get_by_fifa_id(fifa_id)

            if existing is not None:
                if existing.estado != MatchStatus.SCHEDULED:
                    partidos.append(
                        {
                            "fifa_id": fifa_id,
                            "fase": fase,
                            "local": existing.local,
                            "visitante": existing.visitante,
                            "fecha": existing.fecha.isoformat() if existing.fecha else None,
                            "hora_colombia": fx.get("hora_colombia"),
                            "skipped": "ya no está programado",
                        }
                    )
                    continue
                changed = (
                    existing.local != local
                    or existing.visitante != visitante
                    or existing.fecha != fecha
                    or existing.fase != fase
                )
                if changed:
                    teams_changed = (
                        existing.local != local or existing.visitante != visitante
                    )
                    existing.local = local
                    existing.visitante = visitante
                    existing.fecha = fecha
                    existing.fase = fase
                    if teams_changed:
                        self._clear_match_predictions(existing.id)
                    updated += 1
            else:
                self.matches.create(
                    fifa_id=fifa_id,
                    grupo=None,
                    fase=fase,
                    local=local,
                    visitante=visitante,
                    fecha=fecha,
                    estado=MatchStatus.SCHEDULED,
                )
                created += 1

            partidos.append(
                {
                    "fifa_id": fifa_id,
                    "fase": fase,
                    "local": local,
                    "visitante": visitante,
                    "fecha": fecha.isoformat(),
                    "hora_colombia": fx.get("hora_colombia"),
                }
            )

        return {"created": created, "updated": updated, "partidos": partidos}

    def _pairs_for_advance(self, from_fase: str, current: list) -> list[tuple[str, str]]:
        winner_fn = lambda m: m.classified_winner()
        if from_fase == FASE_R32:
            return pair_winners_r32_to_r16(current, winner_fn)
        if from_fase == FASE_R16:
            return pair_winners_r16_to_qf(current, winner_fn)
        if from_fase == FASE_QF:
            return pair_winners_qf_to_sf(current, winner_fn)
        if from_fase == FASE_SF:
            return pair_winners_sf_to_final(current, winner_fn)
        raise ValueError(f"Fase no soportada: {from_fase}")

    def _clear_match_predictions(self, match_id: int) -> None:
        """Borra predicciones (y puntajes) de un partido cuyos equipos se corrigieron."""
        from app.models.score import Score
        from app.repositories.prediction_repository import PredictionRepository

        for pred in PredictionRepository(self.db).list_for_match(match_id):
            self.db.delete(pred)
        for score in self.db.scalars(select(Score).where(Score.match_id == match_id)):
            self.db.delete(score)
        self.db.flush()

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
            for f in (FASE_R16, FASE_QF, FASE_SF, FASE_3RD, FASE_FINAL)
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
    for fase in (FASE_R16, FASE_QF, FASE_SF, FASE_3RD, FASE_FINAL):
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


