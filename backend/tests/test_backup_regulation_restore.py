"""Restore de backup no debe copiar marcador final con TE a los 90 minutos."""
from __future__ import annotations

from app.models.match import Match, MatchStatus
from app.services.backup_service import BackupService


def test_restore_knockout_does_not_copy_final_to_90min(db):
    match = Match(
        fifa_id="KO-R32-10",
        fase="Dieciseisavos de final",
        local="Bélgica",
        visitante="Senegal",
        estado=MatchStatus.FINISHED,
        goles_local=3,
        goles_visitante=2,
    )
    db.add(match)
    db.commit()

    data = {
        "participants": [],
        "users": [],
        "predictions": [],
        "position_predictions": [],
        "match_results": [
            {
                "fifa_id": "KO-R32-10",
                "local": "Bélgica",
                "visitante": "Senegal",
                "goles_local": 3,
                "goles_visitante": 2,
                "estado": "FINISHED",
                "fase": "Dieciseisavos de final",
            }
        ],
        "scores": [],
    }
    BackupService(db).restore_data(data)
    db.refresh(match)

    assert match.goles_local == 3
    assert match.goles_visitante == 2
    assert match.goles_local_90 is None
    assert match.goles_visitante_90 is None


def test_restore_group_stage_sets_90_equal_final(db):
    match = Match(
        fifa_id="WC-A-1",
        fase="Fase de grupos",
        grupo="A",
        local="México",
        visitante="Sudáfrica",
        estado=MatchStatus.FINISHED,
    )
    db.add(match)
    db.commit()

    data = {
        "participants": [],
        "users": [],
        "predictions": [],
        "position_predictions": [],
        "match_results": [
            {
                "fifa_id": "WC-A-1",
                "local": "México",
                "visitante": "Sudáfrica",
                "goles_local": 2,
                "goles_visitante": 0,
                "estado": "FINISHED",
                "fase": "Fase de grupos",
            }
        ],
        "scores": [],
    }
    BackupService(db).restore_data(data)
    db.refresh(match)

    assert match.goles_local_90 == 2
    assert match.goles_visitante_90 == 0
