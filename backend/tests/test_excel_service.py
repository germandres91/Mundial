"""Tests del servicio de importación de Excel."""
from __future__ import annotations

import pandas as pd
import pytest

from app.models.match import Match, MatchStatus
from app.repositories.participant_repository import ParticipantRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.excel_service import DEFAULT_RULES, ExcelImportError, ExcelService


@pytest.fixture()
def match(db):
    m = Match(fifa_id="X-1", local="A", visitante="B", estado=MatchStatus.SCHEDULED)
    db.add(m)
    db.commit()
    return m


def test_seed_default_rules(db):
    count = ExcelService(db).import_rules(path="__no_existe__.xlsx")
    assert count == len(DEFAULT_RULES)


def test_import_rules_from_file(db, tmp_path):
    file = tmp_path / "reglas.xlsx"
    pd.DataFrame(
        [{"code": "EXACT", "descripcion": "Exacto", "puntos": 10, "activo": True}]
    ).to_excel(file, index=False)

    count = ExcelService(db).import_rules(path=str(file))
    # 1 del Excel + el resto de defaults completados (incluye POS_1..POS_4)
    assert count == len(DEFAULT_RULES)

    from app.repositories.scoring_rule_repository import ScoringRuleRepository

    rules = ScoringRuleRepository(db)
    assert rules.get_by_code("EXACT").puntos == 10
    assert rules.get_by_code("POS_1").puntos == 10


def test_import_predictions(db, match, tmp_path):
    file = tmp_path / "preds.xlsx"
    pd.DataFrame(
        [
            {
                "nombre": "Ana",
                "email": "ana@test.com",
                "fifa_id": "X-1",
                "pred_local": 2,
                "pred_visitante": 1,
            }
        ]
    ).to_excel(file, index=False)

    result = ExcelService(db).import_predictions(path=str(file))
    assert result["participantes_creados"] == 1
    assert result["predicciones_importadas"] == 1

    participant = ParticipantRepository(db).get_by_email("ana@test.com")
    assert participant is not None
    preds = PredictionRepository(db).list(participant_id=participant.id)
    assert preds[0].pred_local == 2


def test_import_predictions_missing_file(db):
    with pytest.raises(ExcelImportError):
        ExcelService(db).import_predictions(path="__no_existe__.xlsx")
