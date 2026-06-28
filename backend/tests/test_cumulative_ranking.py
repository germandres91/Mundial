"""Ranking acumulativo entre fase de grupos y eliminatorias."""
from __future__ import annotations

from datetime import datetime, timezone

from app.models.match import Match, MatchStatus
from app.repositories.prediction_repository import PredictionRepository
from app.services.knockout_service import FASE_R32
from app.services.ranking_service import RankingService
from app.services.scoring_service import ScoringService


def _group_match(db, sample_match, *, fifa_id="WC-G-1"):
    m = Match(
        fifa_id=fifa_id,
        grupo="A",
        fase="Fase de grupos",
        local="México",
        visitante="Brasil",
        goles_local=2,
        goles_visitante=1,
        estado=MatchStatus.FINISHED,
        fecha=datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc),
    )
    db.add(m)
    db.commit()
    return m


def _ko_match(db):
    m = Match(
        fifa_id="KO-R32-1",
        grupo=None,
        fase=FASE_R32,
        local="Sudáfrica",
        visitante="Canadá",
        goles_local=1,
        goles_visitante=0,
        estado=MatchStatus.FINISHED,
        fecha=datetime(2026, 6, 28, 19, 0, tzinfo=timezone.utc),
    )
    db.add(m)
    db.commit()
    return m


def test_ranking_sums_group_and_knockout(db, sample_participants):
    p1, p2 = sample_participants
    group = _group_match(db, None)
    knockout = _ko_match(db)
    preds = PredictionRepository(db)
    preds.upsert(p1.id, group.id, 2, 1)
    preds.upsert(p1.id, knockout.id, 1, 0)
    preds.upsert(p2.id, group.id, 0, 0)
    preds.upsert(p2.id, knockout.id, 0, 1)
    db.commit()

    ScoringService(db).recalculate_all()
    rows = {r.participant_id: r for r in RankingService(db).get_ranking()}

    assert rows[p1.id].puntos_totales == 10  # 5 grupos + 5 eliminatorias
    assert rows[p2.id].puntos_totales == 0


def test_backup_restore_preserves_scores(db, sample_participants, sample_match):
    from app.services.backup_service import BackupService

    p = sample_participants[0]
    sample_match.estado = MatchStatus.FINISHED
    sample_match.goles_local = 2
    sample_match.goles_visitante = 1
    PredictionRepository(db).upsert(p.id, sample_match.id, 2, 1)
    db.commit()
    ScoringService(db).recalculate_all()

    data = BackupService(db).export_data()
    assert len(data.get("match_results", [])) >= 1
    assert len(data.get("scores", [])) >= 1

    # Simula pérdida de puntajes
    from app.models.score import Score

    db.query(Score).delete()
    db.commit()
    assert RankingService(db).get_ranking()[0].puntos_totales == 0

    BackupService(db).restore_data(data)
    RankingService(db).recalculate()
    assert RankingService(db).get_ranking()[0].puntos_totales >= 5
