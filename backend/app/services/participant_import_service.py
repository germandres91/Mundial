"""Importa un participante completo (predicciones + top-4) desde el formulario Excel."""
from __future__ import annotations

import json
import re
import unicodedata

from sqlalchemy.orm import Session

from app.core.config import resolve_path
from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.repositories.match_repository import MatchRepository
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.formulario_parser import ParsedFormulario, parse_formulario

logger = get_logger(__name__)


def _norm_name(value: str) -> str:
    base = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", base.lower()).strip()


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
                fifa_guess = f"WC-{pm.grupo}-{i}"
                match = self.matches.get_by_fifa_id(fifa_guess)
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

    def _email_map_from_users_seed(self) -> dict[str, str]:
        """Mapa nombre-normalizado -> email desde data/users_seed.json."""
        path = resolve_path("data/users_seed.json")
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
        mapping: dict[str, str] = {}
        for item in payload.get("usuarios", []):
            nombre = _norm_name(str(item.get("nombre", "")))
            email = str(item.get("email", "")).strip().lower()
            if nombre and email:
                mapping[nombre] = email
        return mapping

    def import_seed_formularios(self) -> dict:
        """Importa todos los formularios de data/formularios/ (idempotente).

        El nombre de archivo es el nombre del participante. El email se toma de
        users_seed.json (si coincide el nombre) para enlazar con su cuenta; si
        no, se genera. Omite participantes que ya tienen predicciones.
        """
        folder = resolve_path("data/formularios")
        if not folder.exists():
            return {"importados": 0, "omitidos": 0}

        email_map = self._email_map_from_users_seed()
        importados = 0
        omitidos = 0
        detalle: list[str] = []
        for file in sorted(folder.glob("*.xlsm")) + sorted(folder.glob("*.xlsx")):
            nombre = file.stem.strip()
            email = email_map.get(_norm_name(nombre)) or _slug_email(nombre)

            existing = self.participants.get_by_email(email)
            if existing and self.predictions.list(participant_id=existing.id):
                omitidos += 1
                continue
            try:
                res = self.import_formulario(str(file), nombre=nombre, email=email)
                importados += 1
                detalle.append(f"{nombre}: {res['predicciones_importadas']} preds")
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo importar formulario: %s", file.name)

        logger.info("Formularios semilla importados: %d (omitidos %d)", importados, omitidos)
        return {"importados": importados, "omitidos": omitidos, "detalle": detalle}
