"""Generación de partidos de eliminatorias a partir de resultados reales."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

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

    def advance_round_of_32(self) -> dict:
        """Crea los 16 partidos de dieciseisavos con los clasificados reales."""
        existing = [
            m for m in self.matches.list(fase=FASE_R32) if m.fifa_id and m.fifa_id.startswith("KO-R32-")
        ]
        if existing:
            return {
                "created": 0,
                "already_exists": len(existing),
                "message": "Los dieciseisavos ya están creados",
            }

        teams = self._qualified_teams()
        order = seed_order(32)
        slots = [teams[i - 1] if i <= len(teams) else None for i in order]

        base = datetime.now(timezone.utc) + timedelta(days=1)
        created = 0
        match_num = 0
        for i in range(0, 32, 2):
            match_num += 1
            a, b = slots[i], slots[i + 1]
            if not a or not b:
                continue
            fifa_id = f"KO-R32-{match_num}"
            if self.matches.get_by_fifa_id(fifa_id):
                continue
            self.matches.create(
                fifa_id=fifa_id,
                grupo=None,
                fase=FASE_R32,
                local=a["equipo"],
                visitante=b["equipo"],
                fecha=base + timedelta(hours=4 * match_num),
                estado=MatchStatus.SCHEDULED,
            )
            created += 1

        self.db.commit()
        logger.info("Dieciseisavos creados: %d partidos", created)
        return {
            "created": created,
            "clasificados": [t["equipo"] for t in teams],
            "fase": FASE_R32,
        }

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

        # Empareja ganadores en orden de fifa_id
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
            out["clasificados_disponibles"] = len(self._qualified_teams())
        except ValueError:
            out["clasificados_disponibles"] = 0
        return out
