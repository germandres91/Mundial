"""Inicializa la base de datos con el torneo y el participante inicial.

Crea tablas -> reglas -> calendario del torneo (12 grupos, 72 partidos) ->
importa el formulario del participante inicial -> recalcula ranking.

Uso (desde la raíz):
    python scripts/seed_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import resolve_path  # noqa: E402
from app.core.database import SessionLocal, init_db  # noqa: E402
from app.services.excel_service import ExcelService  # noqa: E402
from app.services.participant_import_service import ParticipantImportService  # noqa: E402
from app.services.ranking_service import RankingService  # noqa: E402
from app.services.scoring_service import ScoringService  # noqa: E402
from app.services.tournament_service import TournamentService  # noqa: E402


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        print("1/4 Importando reglas de puntaje...")
        ExcelService(db).import_rules()

        print("2/4 Creando calendario del torneo (12 grupos, 72 partidos)...")
        TournamentService(db).seed_schedule()

        print("3/4 Importando formulario de German Andres Bello Garcia...")
        formulario = resolve_path("data/formulario_german_bello.xlsm")
        if formulario.exists():
            result = ParticipantImportService(db).import_formulario(
                str(formulario),
                nombre="German Andres Bello Garcia",
                email="german.andres.bello.garcia@mundial2026.com",
            )
            print(f"     {result}")
        else:
            print(f"     [aviso] No se encontró {formulario}")

        print("4/4 Puntuando y recalculando ranking...")
        ScoringService(db).recalculate_all()
        RankingService(db).recalculate()

        print("Seed completado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
