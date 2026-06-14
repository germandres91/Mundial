"""Pruebas de la gráfica 'Carrera al mundial' (puntaje acumulado)."""
from __future__ import annotations

from app.models.match import Match, MatchStatus
from app.models.score import Score
from app.services.dashboard_service import DashboardService


def _finished_match(db, fifa_id: str, local: str, visitante: str) -> Match:
    m = Match(
        fifa_id=fifa_id,
        grupo="A",
        fase="Fase de grupos",
        local=local,
        visitante=visitante,
        estado=MatchStatus.FINISHED,
    )
    db.add(m)
    db.commit()
    return m


def test_race_acumulado_por_partido(db, sample_participants):
    ana, beto = sample_participants
    m1 = _finished_match(db, "R-1", "México", "Brasil")
    m2 = _finished_match(db, "R-2", "Francia", "Canadá")
    db.add_all(
        [
            Score(participant_id=ana.id, match_id=m1.id, puntos=3),
            Score(participant_id=ana.id, match_id=m2.id, puntos=2),
            Score(participant_id=beto.id, match_id=m1.id, puntos=1),
        ]
    )
    db.commit()

    race = DashboardService(db).race_to_cup()

    assert len(race.partidos) == 2
    assert race.partidos[0].orden == 1
    assert race.partidos[0].etiqueta == "México vs Brasil"

    series = {s.nombre: s.puntos for s in race.series}
    assert series["Ana"] == [3, 5]  # acumulado: 3, luego 3+2
    assert series["Beto"] == [1, 1]  # solo sumó en el primero
    # La serie líder va primero (orden por puntaje final desc).
    assert race.series[0].nombre == "Ana"


def test_race_sin_partidos_finalizados(db, sample_participants):
    race = DashboardService(db).race_to_cup()
    assert race.partidos == []
    assert all(s.puntos == [] for s in race.series)
