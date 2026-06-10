"""Genera el calendario del torneo y los datos mock desde el formulario Excel.

Lee el 'Formulario apuesta' y produce:
  - data/tournament_2026.json : estructura de grupos y partidos (sin marcador)
  - data/mock_matches.json    : partidos para el proveedor mock (con fechas)

Uso:
    python scripts/build_tournament.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.services.formulario_parser import parse_formulario  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SOURCE = DATA / "formulario_german_bello.xlsm"

# Inicio de la fase de grupos del Mundial 2026
KICKOFF = datetime(2026, 6, 11, 18, 0, tzinfo=timezone.utc)


def main() -> None:
    parsed = parse_formulario(SOURCE)
    grupos = parsed.grupos

    tournament = {"grupos": []}
    mock = []
    counters: dict[str, int] = {}
    match_index = 0

    for m in parsed.matches:
        counters[m.grupo] = counters.get(m.grupo, 0) + 1
        n = counters[m.grupo]
        fifa_id = f"WC-{m.grupo}-{n}"
        # Distribuye los partidos cada 4 horas a partir del kickoff
        fecha = KICKOFF + timedelta(hours=4 * match_index)
        match_index += 1
        mock.append(
            {
                "fifa_id": fifa_id,
                "grupo": m.grupo,
                "fase": "Fase de grupos",
                "local": m.local,
                "visitante": m.visitante,
                "fecha": fecha.isoformat(),
                "estado": "SCHEDULED",
            }
        )

    for grupo, equipos in grupos.items():
        partidos = [
            {"fifa_id": mm["fifa_id"], "local": mm["local"], "visitante": mm["visitante"]}
            for mm in mock
            if mm["grupo"] == grupo
        ]
        tournament["grupos"].append({"grupo": grupo, "equipos": equipos, "partidos": partidos})

    (DATA / "tournament_2026.json").write_text(
        json.dumps(tournament, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA / "mock_matches.json").write_text(
        json.dumps(mock, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Grupos: {len(grupos)} | Partidos: {len(mock)}")
    print(f"Top-4 pronóstico: {[(p.posicion, p.equipo) for p in parsed.posiciones]}")
    print("Generados data/tournament_2026.json y data/mock_matches.json")


if __name__ == "__main__":
    main()
