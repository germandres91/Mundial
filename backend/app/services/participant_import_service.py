"""Importa un participante completo (predicciones + top-4) desde el formulario Excel."""
from __future__ import annotations

import re
import unicodedata

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.formulario_parser import ParsedFormulario, parse_formulario

logger = get_logger(__name__)


def _slug_email(nombre: str) -> str:
    base = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-zA-Z0-9]+", ".", base).strip(".").lower()
    return f"{base or 'participante'}@mundial2026.com"


class ParticipantImportService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.participants = ParticipantRepository(db)
        self.matches = MatchRepository(db)
        self.predictions = PredictionRepository(db)
        self.positions = PositionPredictionRepository(db)

    def import_formulario(
        self, source: bytes | str, nombre: str, email: str | None = None
    ) -> dict:
        parsed: ParsedFormulario = parse_formulario(source)
        if not parsed.matches:
            raise ValueError("El formulario no contiene partidos reconocibles.")

        email = (email or _slug_email(nombre)).strip().lower()
        participant = self.participants.get_by_email(email)
        if participant is None:
            participant = self.participants.create(nombre=nombre.strip(), email=email)
        else:
            participant.nombre = nombre.strip()

        # Índice de partidos existentes por (grupo, local, visitante)
        existing = {
            (m.grupo, m.local, m.visitante): m
            for m in self.matches.list()
        }

        imported = 0
        created_matches = 0
        for i, pm in enumerate(parsed.matches, start=1):
            key = (pm.grupo, pm.local, pm.visitante)
            match = existing.get(key)
            if match is None:
                match = self.matches.create(
                    fifa_id=f"WC-{pm.grupo}-{i}",
                    grupo=pm.grupo,
                    fase="Fase de grupos",
                    local=pm.local,
                    visitante=pm.visitante,
                    estado=MatchStatus.SCHEDULED,
                )
                existing[key] = match
                created_matches += 1
            self.db.flush()
            self.predictions.upsert(
                participant_id=participant.id,
                match_id=match.id,
                pred_local=pm.goles_local,
                pred_visitante=pm.goles_visitante,
            )
            imported += 1

        for pos in parsed.posiciones:
            # El bonus se calcula solo contra el resultado real (FinalPosition),
            # nunca se preasigna desde el formulario.
            self.positions.upsert(
                participant_id=participant.id,
                posicion=pos.posicion,
                equipo=pos.equipo,
                puntos=0,
            )

        self.db.commit()
        result = {
            "participant_id": participant.id,
            "nombre": participant.nombre,
            "predicciones_importadas": imported,
            "partidos_creados": created_matches,
            "top4": [(p.posicion, p.equipo) for p in parsed.posiciones],
        }
        logger.info("Formulario importado: %s", result)
        return result
