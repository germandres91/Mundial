"""Genera archivos Excel de ejemplo: predicciones y reglas de puntaje.

Uso:
    python scripts/generate_sample_data.py
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

PARTICIPANTS = [
    ("Ana Torres", "ana@example.com"),
    ("Carlos Ruiz", "carlos@example.com"),
    ("Lucía Gómez", "lucia@example.com"),
    ("Diego Martín", "diego@example.com"),
    ("Sofía Vega", "sofia@example.com"),
    ("Mateo Díaz", "mateo@example.com"),
]


def generate_rules() -> None:
    rules = pd.DataFrame(
        [
            {"code": "EXACT", "descripcion": "Marcador exacto", "puntos": 5, "activo": True},
            {"code": "WINNER_GOALS", "descripcion": "Ganador + goles del ganador", "puntos": 3, "activo": True},
            {"code": "WINNER", "descripcion": "Ganador correcto", "puntos": 2, "activo": True},
            {"code": "DRAW", "descripcion": "Empate correcto", "puntos": 1, "activo": True},
            {"code": "NONE", "descripcion": "Sin acierto", "puntos": 0, "activo": True},
        ]
    )
    out = DATA / "reglas_puntaje.xlsx"
    rules.to_excel(out, index=False)
    print(f"Reglas generadas: {out}")


def generate_predictions() -> None:
    matches_file = DATA / "mock_matches.json"
    matches = json.loads(matches_file.read_text(encoding="utf-8"))

    rng = random.Random(2026)
    rows = []
    for nombre, email in PARTICIPANTS:
        for match in matches:
            rows.append(
                {
                    "nombre": nombre,
                    "email": email,
                    "fifa_id": match["fifa_id"],
                    "local": match["local"],
                    "visitante": match["visitante"],
                    "pred_local": rng.randint(0, 4),
                    "pred_visitante": rng.randint(0, 4),
                }
            )
    df = pd.DataFrame(rows)
    out = DATA / "predicciones.xlsx"
    df.to_excel(out, index=False)
    print(f"Predicciones generadas: {out} ({len(df)} filas)")


if __name__ == "__main__":
    generate_rules()
    generate_predictions()
    print("Listo. Datos de ejemplo creados en /data")
