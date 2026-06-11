"""Tests del puntaje por posiciones finales (1° a 4°)."""
from __future__ import annotations

from app.models.position_prediction import PositionPrediction
from app.repositories.final_position_repository import FinalPositionRepository
from app.services.excel_service import ExcelService
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService


def _seed_predictions(db, participant_id, equipos):
    for pos, equipo in enumerate(equipos, start=1):
        db.add(
            PositionPrediction(
                participant_id=participant_id, posicion=pos, equipo=equipo, puntos=0
            )
        )
    db.commit()


def test_default_position_rules_seeded(db):
    ExcelService(db).import_rules(path="__none__")
    points = ScoringService(db)._points_map()
    assert points["POS_1"] == 10
    assert points["POS_2"] == 9
    assert points["POS_3"] == 7
    assert points["POS_4"] == 5


def test_score_positions_awards_bonus(db, sample_participants):
    ExcelService(db).import_rules(path="__none__")
    p1, p2 = sample_participants
    # p1 acierta campeón y 3er puesto; p2 acierta los 4
    _seed_predictions(db, p1.id, ["Argentina", "Brasil", "Francia", "Croacia"])
    _seed_predictions(db, p2.id, ["Argentina", "España", "Francia", "Portugal"])

    repo = FinalPositionRepository(db)
    repo.upsert(1, "Argentina")
    repo.upsert(2, "España")
    repo.upsert(3, "Francia")
    repo.upsert(4, "Croacia")
    db.commit()

    ScoringService(db).score_positions()
    db.commit()

    # p1: POS_1 (10) + POS_3 (7) = 17
    preds_p1 = {pp.posicion: pp.puntos for pp in repo_list_positions(db, p1.id)}
    assert preds_p1[1] == 10
    assert preds_p1[2] == 0
    assert preds_p1[3] == 7
    assert preds_p1[4] == 5  # acertó Croacia 4°

    rows = RankingService(db).recalculate()
    by_id = {r.participant_id: r for r in rows}
    # p2 acierta 1,2,3 => 10+9+7 = 26; p1 => 10+7+5 = 22
    assert by_id[p2.id].puntos_posiciones == 26
    assert by_id[p1.id].puntos_posiciones == 22
    assert by_id[p2.id].posicion == 1  # más puntos => primero


def test_score_positions_matches_across_languages(db, sample_participants):
    ExcelService(db).import_rules(path="__none__")
    p1, _ = sample_participants
    _seed_predictions(db, p1.id, ["Brasil", "", "", ""])

    # Resultado oficial en inglés debe emparejar con "Brasil"
    FinalPositionRepository(db).upsert(1, "Brazil")
    db.commit()

    ScoringService(db).score_positions()
    db.commit()

    preds = {pp.posicion: pp.puntos for pp in repo_list_positions(db, p1.id)}
    assert preds[1] == 10


def repo_list_positions(db, participant_id):
    from app.repositories.position_prediction_repository import (
        PositionPredictionRepository,
    )

    return PositionPredictionRepository(db).list_for(participant_id)


def test_set_final_positions_endpoint(client, auth_headers, db):
    from app.models.participant import Participant

    p = Participant(nombre="Caro", email="caro@test.com")
    db.add(p)
    db.commit()
    _seed_predictions(db, p.id, ["Argentina", "Brasil", "Francia", "Croacia"])

    # Sin sesión: 401
    assert client.put("/api/v1/admin/final-positions", json={"posiciones": []}).status_code == 401

    payload = {
        "posiciones": [
            {"posicion": 1, "equipo": "Argentina"},
            {"posicion": 2, "equipo": "Brasil"},
            {"posicion": 3, "equipo": "Francia"},
            {"posicion": 4, "equipo": "Croacia"},
        ]
    }
    resp = client.put("/api/v1/admin/final-positions", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["aciertos"] == 4

    got = client.get("/api/v1/admin/final-positions", headers=auth_headers).json()
    assert got["posiciones"][0]["equipo"] == "Argentina"
    assert got["posiciones"][0]["puntos"] == 10
