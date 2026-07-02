#!/usr/bin/env python3
"""Recalcula puntajes usando solo marcadores de 90 minutos (idempotente).

Uso:
    python scripts/apply_90min_scoring.py

Crea un backup de seguridad antes de modificar puntajes.
No elimina predicciones ni usuarios.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.database import SessionLocal, init_db  # noqa: E402
from app.services.regulation_scoring_service import RegulationScoringService  # noqa: E402
from app.services.tournament_service import TournamentService  # noqa: E402


def main() -> int:
    db = SessionLocal()
    try:
        init_db()
        TournamentService(db).seed_schedule()
        result = RegulationScoringService(db).recalculate_all(create_backup=True)
        print("Recálculo completado:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
