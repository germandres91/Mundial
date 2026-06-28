"""Tests de predicciones de eliminatorias y avance de rondas."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.models.match import Match, MatchStatus
from app.models.user import UserRole
from app.services.auth_service import AuthService
from app.services.knockout_service import FASE_R32, KnockoutService
from app.services.prediction_submission_service import (
    PredictionSubmissionError,
    PredictionSubmissionService,
)


def _knockout_match(db, *, fifa_id="KO-R32-1", kickoff_hours=48):
    m = Match(
        fifa_id=fifa_id,
        grupo=None,
        fase=FASE_R32,
        local="Equipo A",
        visitante="Equipo B",
        fecha=datetime.now(timezone.utc) + timedelta(hours=kickoff_hours),
        estado=MatchStatus.SCHEDULED,
    )
    db.add(m)
    db.commit()
    return m


def _participant_user(db, participant):
    AuthService(db).register(
        email=participant.email,
        nombre=participant.nombre,
        password="secret1",
        role=UserRole.PARTICIPANT,
        participant_id=participant.id,
    )
    user = AuthService(db).users.get_by_email(participant.email)
    assert user is not None
    return user


def test_submit_knockout_prediction_locked(db, sample_participants):
    p = sample_participants[0]
    user = _participant_user(db, p)
    match = _knockout_match(db)
    svc = PredictionSubmissionService(db)

    result = svc.submit(user, match.id, 2, 1)
    assert result["status"] == "submitted"
    assert result["prediction_id"]

    pred = svc.predictions.get_for(p.id, match.id)
    assert pred is not None
    assert pred.locked_at is not None
    assert pred.pred_local == 2
    assert pred.pred_visitante == 1


def test_submit_twice_raises_locked(db, sample_participants):
    p = sample_participants[0]
    user = _participant_user(db, p)
    match = _knockout_match(db)
    svc = PredictionSubmissionService(db)
    svc.submit(user, match.id, 1, 0)

    try:
        svc.submit(user, match.id, 3, 3)
        assert False, "debía fallar"
    except PredictionSubmissionError as exc:
        assert exc.code == "locked"


def test_late_submission_pending_and_admin_approve(db, sample_participants):
    p = sample_participants[0]
    user = _participant_user(db, p)
    admin = AuthService(db).register(
        email="admin2@test.com",
        nombre="Admin2",
        password="secret1",
        role=UserRole.ADMIN,
    )
    match = _knockout_match(db, kickoff_hours=-1)
    svc = PredictionSubmissionService(db)

    result = svc.submit(user, match.id, 0, 2)
    assert result["status"] == "pending_approval"

    pending = svc.late.list()
    assert len(pending) == 1
    req_id = pending[0].id

    approved = svc.approve_late(req_id, admin, note="ok")
    assert approved["status"] == "approved"

    pred = svc.predictions.get_for(p.id, match.id)
    assert pred is not None
    assert pred.locked_at is not None
    assert pred.pred_local == 0
    assert pred.pred_visitante == 2


def test_submission_matrix(db, sample_participants):
    p1, p2 = sample_participants
    u1 = _participant_user(db, p1)
    match = _knockout_match(db)
    svc = PredictionSubmissionService(db)
    svc.submit(u1, match.id, 2, 0)

    matrix = svc.submission_matrix()
    assert len(matrix["matches"]) == 1
    assert len(matrix["participants"]) == 2
    row1 = next(r for r in matrix["participants"] if r["participant_id"] == p1.id)
    row2 = next(r for r in matrix["participants"] if r["participant_id"] == p2.id)
    assert row1["cells"][0]["submitted"] is True
    assert row2["cells"][0]["submitted"] is False


def test_knockout_advance_r32_from_groups(db, monkeypatch):
    """Genera dieciseisavos cuando hay 32 clasificados simulados."""
    teams = [{"equipo": f"Team {i}", "grupo": chr(65 + i // 4)} for i in range(32)]

    class FakeTournament:
        def _standings_from(self, _):
            return {}

        def _qualified_from(self, _):
            return teams

    svc = KnockoutService(db)
    monkeypatch.setattr(svc, "tournament", FakeTournament())

    result = svc.advance_round_of_32()
    assert result["created"] == 16
    assert len(svc.matches.list(fase=FASE_R32)) == 16

    again = svc.advance_round_of_32()
    assert again["created"] == 0


def test_round_predictions_api(client, db, sample_participants):
    p = sample_participants[0]
    AuthService(db).register(
        email=p.email,
        nombre=p.nombre,
        password="secret1",
        role=UserRole.PARTICIPANT,
        participant_id=p.id,
    )
    login = client.post(
        "/api/v1/auth/login", json={"email": p.email, "password": "secret1"}
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    match = _knockout_match(db)
    resp = client.post(
        "/api/v1/round-predictions/submit",
        json={"match_id": match.id, "pred_local": 1, "pred_visitante": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "submitted"

    matches = client.get("/api/v1/round-predictions/matches", headers=headers)
    assert matches.status_code == 200
    row = next(m for m in matches.json() if m["match_id"] == match.id)
    assert row["submitted"] is True
