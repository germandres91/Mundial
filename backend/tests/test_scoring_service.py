"""Tests unitarios del servicio de puntajes."""
from __future__ import annotations

import pytest

from app.models.match import MatchStatus
from app.models.prediction import Prediction
from app.services.scoring_service import ScoringService


@pytest.fixture()
def service(db):
    return ScoringService(db)


@pytest.mark.parametrize(
    "pred,real,expected_code,expected_points",
    [
        ((2, 1), (2, 1), "EXACT", 5),         # marcador exacto
        ((2, 0), (2, 1), "WINNER_GOALS", 3),  # ganador local + goles ganador (2)
        ((3, 1), (2, 1), "WINNER", 2),        # ganador local, goles del ganador distintos
        ((4, 1), (2, 1), "WINNER", 2),        # ganador local pero goles distintos
        ((1, 1), (2, 2), "DRAW", 1),          # empate correcto
        ((2, 1), (0, 3), "NONE", 0),          # resultado equivocado
    ],
)
def test_evaluate_rules(service, pred, real, expected_code, expected_points):
    result = service.evaluate(pred[0], pred[1], real[0], real[1])
    assert result.code == expected_code
    assert result.puntos == expected_points


def test_winner_goals_away(service):
    # Visitante gana 0-2, predijo 1-2 -> ganador + goles del ganador (2)
    result = service.evaluate(1, 2, 0, 2)
    assert result.code == "WINNER_GOALS"
    assert result.puntos == 3


def test_score_match_persists(db, service, sample_participants, sample_match):
    p1, p2 = sample_participants
    mid = sample_match.id
    db.add(Prediction(participant_id=p1.id, match_id=mid, pred_local=1, pred_visitante=0))
    db.add(Prediction(participant_id=p2.id, match_id=mid, pred_local=2, pred_visitante=2))
    db.commit()

    sample_match.goles_local = 1
    sample_match.goles_visitante = 0
    sample_match.estado = MatchStatus.FINISHED
    db.commit()

    evaluated = service.score_match(sample_match)
    db.commit()
    assert evaluated == 2

    from app.repositories.score_repository import ScoreRepository

    scores = ScoreRepository(db).list()
    by_participant = {s.participant_id: s.puntos for s in scores}
    assert by_participant[p1.id] == 5  # exacto
    assert by_participant[p2.id] == 0  # falló


def test_score_match_skips_unfinished(service, sample_match):
    assert service.score_match(sample_match) == 0
