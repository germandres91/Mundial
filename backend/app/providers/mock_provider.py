"""Proveedor simulado para desarrollo y pruebas (sin conexión externa)."""
from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.logging import get_logger
from app.models.match import MatchStatus
from app.providers.base import BaseFootballProvider, ProviderMatch

logger = get_logger(__name__)

_DATA_CANDIDATES = [
    Path("data/mock_matches.json"),
    Path("../data/mock_matches.json"),
    Path(__file__).resolve().parents[3] / "data" / "mock_matches.json",
]


class MockProvider(BaseFootballProvider):
    """Genera resultados deterministas/aleatorios a partir de un JSON local.

    Si el archivo no existe, genera un calendario mínimo en memoria. Cada vez
    que se consulta, algunos partidos "programados" pasan a "finalizados" con
    un marcador aleatorio para simular el avance del torneo.
    """

    name = "mock"

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._matches = self._load()

    def _load(self) -> list[ProviderMatch]:
        for candidate in _DATA_CANDIDATES:
            if candidate.exists():
                raw = json.loads(candidate.read_text(encoding="utf-8"))
                return [self._parse(item) for item in raw]
        logger.warning("mock_matches.json no encontrado; generando calendario en memoria")
        return self._generate_default()

    @staticmethod
    def _parse(item: dict) -> ProviderMatch:
        fecha = item.get("fecha")
        return ProviderMatch(
            fifa_id=str(item["fifa_id"]),
            local=item["local"],
            visitante=item["visitante"],
            fecha=datetime.fromisoformat(fecha) if fecha else None,
            grupo=item.get("grupo"),
            fase=item.get("fase"),
            goles_local=item.get("goles_local"),
            goles_visitante=item.get("goles_visitante"),
            estado=MatchStatus(item.get("estado", "SCHEDULED")),
        )

    def _generate_default(self) -> list[ProviderMatch]:
        teams = ["México", "USA", "Canadá", "Argentina", "Brasil", "Francia", "España", "Alemania"]
        base = datetime.now(timezone.utc) - timedelta(days=2)
        matches: list[ProviderMatch] = []
        idx = 1
        for i in range(0, len(teams), 2):
            matches.append(
                ProviderMatch(
                    fifa_id=f"MOCK-{idx}",
                    local=teams[i],
                    visitante=teams[i + 1],
                    fecha=base + timedelta(days=idx),
                    grupo="A",
                    fase="Fase de grupos",
                    estado=MatchStatus.SCHEDULED,
                )
            )
            idx += 1
        return matches

    def fetch_matches(self) -> list[ProviderMatch]:
        now = datetime.now(timezone.utc)
        for match in self._matches:
            if match.estado == MatchStatus.FINISHED:
                continue
            # Simula que partidos cuya fecha ya pasó se finalizan con marcador.
            if match.fecha and match.fecha <= now:
                match.goles_local = self._rng.randint(0, 4)
                match.goles_visitante = self._rng.randint(0, 4)
                match.estado = MatchStatus.FINISHED
        return list(self._matches)
