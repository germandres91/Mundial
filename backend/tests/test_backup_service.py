"""Pruebas del servicio de respaldo y restauración de datos."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models.match import Match, MatchStatus
from app.repositories.position_prediction_repository import PositionPredictionRepository
from app.repositories.prediction_repository import PredictionRepository
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.backup_service import BackupService


def test_export_contains_users_and_predictions(db, sample_participants, sample_match):
    AuthService(db).register(
        email="ana@test.com",
        nombre="Ana",
        password="secret1",
        participant_id=sample_participants[0].id,
    )
    PredictionRepository(db).upsert(sample_participants[0].id, sample_match.id, 2, 1)
    PositionPredictionRepository(db).upsert(sample_participants[0].id, 1, "Brasil", 0)
    db.commit()

    data = BackupService(db).export_data()

    assert data["version"] == 1
    assert any(u["email"] == "ana@test.com" for u in data["users"])
    assert len(data["predictions"]) == 1
    assert data["predictions"][0]["pred_local"] == 2
    assert data["predictions"][0]["fifa_id"] == "T-1"
    assert data["position_predictions"][0]["equipo"] == "Brasil"


def test_restore_into_fresh_database(db, sample_participants, sample_match):
    AuthService(db).register(
        email="ana@test.com",
        nombre="Ana",
        password="secret1",
        participant_id=sample_participants[0].id,
    )
    PredictionRepository(db).upsert(sample_participants[0].id, sample_match.id, 2, 1)
    PositionPredictionRepository(db).upsert(sample_participants[0].id, 1, "Brasil", 0)
    db.commit()
    data = BackupService(db).export_data()

    eng2 = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(eng2)
    db2 = sessionmaker(bind=eng2)()
    db2.add(
        Match(
            fifa_id="T-1",
            grupo="A",
            fase="Fase de grupos",
            local="México",
            visitante="Brasil",
            estado=MatchStatus.SCHEDULED,
        )
    )
    db2.commit()

    summary = BackupService(db2).restore_data(data)

    assert summary["participantes_creados"] == 2
    assert summary["usuarios_creados"] == 1
    assert summary["predicciones_restauradas"] == 1
    assert summary["posiciones_restauradas"] == 1

    user = UserRepository(db2).get_by_email("ana@test.com")
    assert user is not None
    assert user.participant_id is not None
    preds = PredictionRepository(db2).list()
    assert len(preds) == 1 and preds[0].pred_local == 2


def test_restore_is_idempotent(db, sample_participants, sample_match):
    PredictionRepository(db).upsert(sample_participants[0].id, sample_match.id, 3, 0)
    db.commit()
    data = BackupService(db).export_data()

    svc = BackupService(db)
    svc.restore_data(data)
    summary = svc.restore_data(data)

    assert summary["usuarios_creados"] == 0
    assert summary["participantes_creados"] == 0
    assert PredictionRepository(db).count() == 1
