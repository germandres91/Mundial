"""Tests del servicio de ranking."""
from __future__ import annotations

from app.models.score import Score
from app.services.ranking_service import RankingService


def test_ranking_orders_by_points(db, sample_participants, sample_match):
    p1, p2 = sample_participants
    mid = sample_match.id
    db.add(Score(participant_id=p1.id, match_id=mid, puntos=5, detalle="Marcador exacto"))
    db.add(Score(participant_id=p2.id, match_id=mid, puntos=2, detalle="Ganador correcto"))
    db.commit()

    rows = RankingService(db).recalculate()
    assert rows[0].participant_id == p1.id
    assert rows[0].posicion == 1
    assert rows[0].puntos_totales == 5
    assert rows[0].aciertos_exactos == 1
    assert rows[1].participant_id == p2.id
    assert rows[1].posicion == 2


def test_get_ranking_reads_persisted(db, sample_participants, sample_match):
    p1, _ = sample_participants
    db.add(Score(participant_id=p1.id, match_id=sample_match.id, puntos=3, detalle="x"))
    db.commit()
    RankingService(db).recalculate()

    rows = RankingService(db).get_ranking()
    assert any(r.participant_id == p1.id and r.puntos_totales == 3 for r in rows)
