"""Servicio de importación automática desde Excel (predicciones y reglas)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.scoring_rule_repository import ScoringRuleRepository
from app.services.scoring_service import DEFAULT_RULES

logger = get_logger(__name__)


class ExcelImportError(Exception):
    """Error de importación de Excel."""


class ExcelService:
    """Importa participantes, predicciones y reglas desde archivos Excel.

    Formato esperado de predicciones (hoja por defecto):
        nombre | email | local | visitante | pred_local | pred_visitante
    o bien:
        nombre | email | fifa_id | pred_local | pred_visitante

    Formato esperado de reglas:
        code | descripcion | puntos | activo
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self.participants = ParticipantRepository(db)
        self.matches = MatchRepository(db)
        self.predictions = PredictionRepository(db)
        self.rules = ScoringRuleRepository(db)

    # ----------------------------- Reglas -----------------------------
    def import_rules(self, path: str | None = None) -> int:
        """Importa reglas de puntaje desde Excel; usa defaults si no existe."""
        file_path = Path(path) if path else settings.rules_file
        if not file_path.exists():
            logger.warning(
                "Excel de reglas no encontrado (%s); usando reglas por defecto", file_path
            )
            return self._seed_default_rules()

        df = pd.read_excel(file_path)
        df.columns = [str(c).strip().lower() for c in df.columns]
        required = {"code", "puntos"}
        if not required.issubset(df.columns):
            raise ExcelImportError(f"El Excel de reglas debe tener columnas {required}")

        count = 0
        for _, row in df.iterrows():
            code = str(row["code"]).strip().upper()
            if not code or code == "NAN":
                continue
            self.rules.upsert(
                code=code,
                descripcion=str(row.get("descripcion", code)),
                puntos=int(row["puntos"]),
                activo=bool(row.get("activo", True)),
            )
            count += 1
        self.db.commit()
        logger.info("Importadas %d reglas de puntaje desde Excel", count)
        return count

    def _seed_default_rules(self) -> int:
        descriptions = {
            "EXACT": "Marcador exacto",
            "WINNER_GOALS": "Ganador + goles del ganador",
            "WINNER": "Ganador correcto",
            "DRAW": "Empate correcto",
            "NONE": "Sin acierto",
        }
        for code, puntos in DEFAULT_RULES.items():
            self.rules.upsert(code=code, descripcion=descriptions[code], puntos=puntos)
        self.db.commit()
        return len(DEFAULT_RULES)

    # -------------------------- Predicciones --------------------------
    def import_predictions(self, path: str | None = None) -> dict[str, int]:
        """Importa participantes y sus predicciones desde Excel."""
        file_path = Path(path) if path else settings.predictions_file
        if not file_path.exists():
            raise ExcelImportError(f"Archivo de predicciones no encontrado: {file_path}")

        df = pd.read_excel(file_path)
        df.columns = [str(c).strip().lower() for c in df.columns]

        if not {"nombre", "email"}.issubset(df.columns):
            raise ExcelImportError("El Excel debe incluir columnas 'nombre' y 'email'")
        if not {"pred_local", "pred_visitante"}.issubset(df.columns):
            raise ExcelImportError("El Excel debe incluir 'pred_local' y 'pred_visitante'")

        created_participants = 0
        imported_predictions = 0
        skipped = 0

        for _, row in df.iterrows():
            email = str(row["email"]).strip().lower()
            nombre = str(row["nombre"]).strip()
            if not email or email == "nan":
                skipped += 1
                continue

            participant = self.participants.get_by_email(email)
            if participant is None:
                participant = self.participants.create(nombre=nombre, email=email)
                created_participants += 1

            match = self._resolve_match(row)
            if match is None:
                skipped += 1
                continue

            try:
                pred_local = int(row["pred_local"])
                pred_visitante = int(row["pred_visitante"])
            except (ValueError, TypeError):
                skipped += 1
                continue

            self.predictions.upsert(
                participant_id=participant.id,
                match_id=match.id,
                pred_local=pred_local,
                pred_visitante=pred_visitante,
            )
            imported_predictions += 1

        self.db.commit()
        result = {
            "participantes_creados": created_participants,
            "predicciones_importadas": imported_predictions,
            "omitidas": skipped,
        }
        logger.info("Importación Excel: %s", result)
        return result

    def _resolve_match(self, row: pd.Series):
        """Localiza el partido por fifa_id o por nombres de equipos."""
        if "fifa_id" in row and not pd.isna(row.get("fifa_id")):
            return self.matches.get_by_fifa_id(str(row["fifa_id"]).strip())
        if {"local", "visitante"}.issubset(row.index):
            local = str(row.get("local", "")).strip()
            visitante = str(row.get("visitante", "")).strip()
            for match in self.matches.list():
                if match.local == local and match.visitante == visitante:
                    return match
        return None
