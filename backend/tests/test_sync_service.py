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


class FlappingProvider(BaseFootballProvider):
    """Simula el tier gratuito: alterna lecturas con y sin marcador."""

    name = "flapping"

    def __init__(self, batches):
        self._batches = batches
        self._i = 0

    def fetch_matches(self):
        batch = self._batches[min(self._i, len(self._batches) - 1)]
        self._i += 1
        return batch


def test_sync_captures_live_score_across_flapping_reads(db, monkeypatch):
    """Aunque la primera lectura venga vacía, el sync combina varias y captura el marcador."""
    import app.services.sync_service as sync_module

    monkeypatch.setattr(sync_module.time, "sleep", lambda *_: None)

    kickoff = datetime.now(timezone.utc) - timedelta(minutes=30)
    own = MatchRepository(db).create(
        fifa_id="WC-A-1",
        local="México",
        visitante="Sudáfrica",
        fecha=kickoff,
        estado=MatchStatus.SCHEDULED,
    )

    empty = ProviderMatch(
        fifa_id="537327",
        local="Mexico",
        visitante="South Africa",
        fecha=kickoff,
        goles_local=None,
        goles_visitante=None,
        estado=MatchStatus.SCHEDULED,
    )
    live = ProviderMatch(
        fifa_id="537327",
        local="Mexico",
        visitante="South Africa",
        fecha=kickoff,
        goles_local=2,
        goles_visitante=0,
        estado=MatchStatus.LIVE,
    )
    provider = FlappingProvider([[empty], [live], [empty]])
    SyncService(db, provider=provider).sync()

    refreshed = MatchRepository(db).get(own.id)
    assert refreshed.estado == MatchStatus.LIVE
    assert refreshed.goles_local == 2
    assert refreshed.goles_visitante == 0


def test_live_match_gives_provisional_points(db):
    """Un partido EN VIVO otorga puntos provisionales en el ranking."""
    ExcelService(db).import_rules(path="__none__")

    match = MatchRepository(db).create(
        fifa_id="WC-A-1",
        local="México",
        visitante="Sudáfrica",
        goles_local=2,
        goles_visitante=0,
        estado=MatchStatus.LIVE,
    )
    exacto = Participant(nombre="Martin", email="martin@test.com")
    ganador = Participant(nombre="Ana", email="ana@test.com")
    db.add_all([exacto, ganador])
    db.commit()
    db.add(
        Prediction(participant_id=exacto.id, match_id=match.id, pred_local=2, pred_visitante=0)
    )
    db.add(
        Prediction(participant_id=ganador.id, match_id=match.id, pred_local=2, pred_visitante=1)
    )
    db.commit()

    from app.services.ranking_service import RankingService

    rows = {r.nombre: r for r in RankingService(db).get_ranking()}
    assert rows["Martin"].puntos_totales == 5  # marcador exacto provisional
    assert rows["Martin"].puntos_en_vivo == 5
    assert rows["Martin"].provisional is True
    assert rows["Ana"].puntos_totales == 3  # ganador + goles del ganador
    assert rows["Ana"].provisional is True
    # El líder provisional es quien acertó el marcador exacto
    assert rows["Martin"].posicion == 1


def test_sync_scores_when_result_arrives_after_finished(db):
    """Si el marcador llega cuando el partido ya estaba finalizado, igual puntúa.

    Reproduce el caso del tier gratuito: el partido se marcó FINISHED sin
    marcador y, en un sync posterior, la API recién entrega el resultado.
    """
    ExcelService(db).import_rules(path="__none__")

    # Partido propio ya FINALIZADO pero sin marcador (lo que pasó en producción)
    own = MatchRepository(db).create(
        fifa_id="WC-A-1",
        local="México",
        visitante="Sudáfrica",
        estado=MatchStatus.FINISHED,
    )
    participant = Participant(nombre="Martin", email="martin@test.com")
    db.add(participant)
    db.commit()
    db.add(
        Prediction(participant_id=participant.id, match_id=own.id, pred_local=2, pred_visitante=0)
    )
    db.commit()

    # La API ahora sí entrega el resultado final 2-0
    final = ProviderMatch(
        fifa_id="537327",
        local="Mexico",
        visitante="South Africa",
        goles_local=2,
        goles_visitante=0,
        estado=MatchStatus.FINISHED,
    )
    SyncService(db, provider=FakeProvider([final])).sync()

    refreshed = MatchRepository(db).get(own.id)
    assert refreshed.goles_local == 2
    assert refreshed.goles_visitante == 0

    from app.repositories.ranking_repository import RankingRepository

    ranking = RankingRepository(db).get(participant.id)
    assert ranking is not None
    assert ranking.puntos_totales == 5  # marcador exacto definitivo


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
