"""Tests de puntuación con marcador de 90 minutos reglamentarios."""
from __future__ import annotations

import pytest

from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.services.scoring_service import ScoringService


@pytest.fixture()
def service(db):
    return ScoringService(db)


@pytest.mark.parametrize(
    "pred,real_90,expected_code,expected_points",
    [
        ((2, 2), (2, 2), "EXACT", 5),
        ((1, 1), (2, 2), "DRAW", 1),
        ((2, 1), (2, 2), "NONE", 0),
        ((3, 2), (2, 2), "NONE", 0),
    ],
)
def test_evaluate_uses_regulation_draw(service, pred, real_90, expected_code, expected_points):
    result = service.evaluate(pred[0], pred[1], real_90[0], real_90[1])
    assert result.code == expected_code
    assert result.puntos == expected_points


def test_belgium_senegal_extra_time_counts_as_draw(db, service, sample_participants):
    """Bélgica 3-2 tras TE; a los 90' fue 2-2 → empate para puntuación."""
    p1, p2 = sample_participants
    match = Match(
        fifa_id="KO-R32-10",
        fase="Dieciseisavos de final",
        local="Bélgica",
        visitante="Senegal",
        goles_local=3,
        goles_visitante=2,
        goles_local_90=2,
        goles_visitante_90=2,
        ganador="Bélgica",
        estado=MatchStatus.FINISHED,
    )
    db.add(match)
    db.flush()
    db.add(Prediction(participant_id=p1.id, match_id=match.id, pred_local=2, pred_visitante=2))
    db.add(Prediction(participant_id=p2.id, match_id=match.id, pred_local=3, pred_visitante=2))
    db.commit()

    service.score_match(match)
    db.commit()

    from app.repositories.score_repository import ScoreRepository

    scores = {s.participant_id: s for s in ScoreRepository(db).list()}
    assert scores[p1.id].puntos == 5
    assert scores[p1.id].detalle == "Marcador exacto"
    assert scores[p2.id].puntos == 0


def test_penalty_shootout_counts_as_draw(db, service, sample_participants):
    """Alemania 1-1 (90') / Paraguay gana penales → empate para puntuación."""
    p1, _p2 = sample_participants
    match = Match(
        fifa_id="KO-R32-2",
        fase="Dieciseisavos de final",
        local="Alemania",
        visitante="Paraguay",
        goles_local=1,
        goles_visitante=1,
        goles_local_90=1,
        goles_visitante_90=1,
        penales_local=3,
        penales_visitante=4,
        ganador="Paraguay",
        estado=MatchStatus.FINISHED,
    )
    db.add(match)
    db.flush()
    db.add(Prediction(participant_id=p1.id, match_id=match.id, pred_local=1, pred_visitante=1))
    db.commit()

    service.score_match(match)
    db.commit()

    from app.repositories.score_repository import ScoreRepository

    score = ScoreRepository(db).list()[0]
    assert score.puntos == 5
    assert score.detalle == "Marcador exacto"


def test_regulation_from_linescores():
    from app.utils.match_scores import penalties_from_linescores, regulation_from_linescores

    home = [{"displayValue": "0"}, {"displayValue": "2"}, {"displayValue": "0"}, {"displayValue": "1"}]
    away = [{"displayValue": "1"}, {"displayValue": "1"}, {"displayValue": "0"}, {"displayValue": "0"}]
    assert regulation_from_linescores(home, away) == (2, 2)

    home_pen = [{"displayValue": "0"}, {"displayValue": "1"}, {"displayValue": "0"}, {"displayValue": "0"}, {"displayValue": "3"}]
    away_pen = [{"displayValue": "1"}, {"displayValue": "0"}, {"displayValue": "0"}, {"displayValue": "0"}, {"displayValue": "4"}]
    assert regulation_from_linescores(home_pen, away_pen) == (1, 1)
    assert penalties_from_linescores(home_pen, away_pen) == (3, 4)
