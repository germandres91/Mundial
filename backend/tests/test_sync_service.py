"""Tests de integración del servicio de sincronización."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.match import MatchStatus
from app.models.participant import Participant
from app.models.prediction import Prediction
from app.providers.base import BaseFootballProvider, ProviderMatch
from app.repositories.match_repository import MatchRepository
from app.services.excel_service import ExcelService
from app.services.sync_service import SyncService


class FakeProvider(BaseFootballProvider):
    name = "fake"

    def __init__(self, matches):
        self._matches = matches

    def fetch_matches(self):
        return self._matches


def test_import_calendar_creates_matches(db):
    matches = [
        ProviderMatch(fifa_id="A-1", local="X", visitante="Y", fase="Grupos"),
        ProviderMatch(fifa_id="A-2", local="W", visitante="Z", fase="Grupos"),
    ]
    service = SyncService(db, provider=FakeProvider(matches))
    assert service.import_calendar() == 2
    assert MatchRepository(db).count() == 2


def test_sync_scores_finished_match(db):
    ExcelService(db).import_rules(path="__none__")  # reglas por defecto

    # Calendario inicial: partido programado
    scheduled = ProviderMatch(
        fifa_id="A-1",
        local="X",
        visitante="Y",
        fecha=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    SyncService(db, provider=FakeProvider([scheduled])).import_calendar()

    match = MatchRepository(db).get_by_fifa_id("A-1")
    participant = Participant(nombre="Ana", email="ana@test.com")
    db.add(participant)
    db.commit()
    db.add(
        Prediction(
            participant_id=participant.id, match_id=match.id, pred_local=1, pred_visitante=0
        )
    )
    db.commit()

    # Ahora el proveedor reporta el partido finalizado 1-0
    finished = ProviderMatch(
        fifa_id="A-1",
        local="X",
        visitante="Y",
        goles_local=1,
        goles_visitante=0,
        estado=MatchStatus.FINISHED,
    )
    result = SyncService(db, provider=FakeProvider([finished])).sync()
    assert result["finalizados_nuevos"] == 1

    from app.repositories.ranking_repository import RankingRepository

    ranking = RankingRepository(db).get(participant.id)
    assert ranking is not None
    assert ranking.puntos_totales == 5  # marcador exacto


def test_sync_matches_by_team_names_and_orientation(db):
    """La API (inglés, orden invertido, id distinto) actualiza el partido propio."""
    ExcelService(db).import_rules(path="__none__")

    # Partido propio en español: Colombia vs Brasil
    own = MatchRepository(db).create(
        fifa_id="WC-A-1",
        local="Colombia",
        visitante="Brasil",
        estado=MatchStatus.SCHEDULED,
    )
    participant = Participant(nombre="Leo", email="leo@test.com")
    db.add(participant)
    db.commit()
    db.add(
        Prediction(
            participant_id=participant.id, match_id=own.id, pred_local=0, pred_visitante=2
        )
    )
    db.commit()

    # La API reporta Brazil 2-0 Colombia (inglés, invertido, id propio de la API)
    api_match = ProviderMatch(
        fifa_id="998877",
        local="Brazil",
        visitante="Colombia",
        goles_local=2,
        goles_visitante=0,
        estado=MatchStatus.FINISHED,
    )
    result = SyncService(db, provider=FakeProvider([api_match])).sync()

    assert result["finalizados_nuevos"] == 1
    assert result["omitidos"] == 0
    # No se crearon partidos nuevos
    assert MatchRepository(db).count() == 1

    refreshed = MatchRepository(db).get(own.id)
    # Orientación corregida: Colombia 0 - 2 Brasil
    assert refreshed.goles_local == 0
    assert refreshed.goles_visitante == 2

    from app.repositories.ranking_repository import RankingRepository

    ranking = RankingRepository(db).get(participant.id)
    assert ranking is not None
    assert ranking.puntos_totales == 5  # acertó marcador exacto 0-2


def test_sync_skips_unknown_matches(db):
    """Partidos de la API que no corresponden al torneo se omiten (no se crean)."""
    ExcelService(db).import_rules(path="__none__")
    foreign = ProviderMatch(
        fifa_id="111",
        local="Italy",
        visitante="Wales",
        goles_local=1,
        goles_visitante=1,
        estado=MatchStatus.FINISHED,
    )
    result = SyncService(db, provider=FakeProvider([foreign])).sync()
    assert result["omitidos"] == 1
    assert result["actualizados"] == 0
    assert MatchRepository(db).count() == 0
