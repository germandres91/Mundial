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


def test_late_submit_allowed_while_match_live(db, sample_participants):
    """KO-R32-1 acepta envío tardío aunque el partido ya esté en juego."""
    p = sample_participants[0]
    user = _participant_user(db, p)
    svc = PredictionSubmissionService(db)
    KnockoutService(db).advance_round_of_32()
    match = svc.matches.get_by_fifa_id("KO-R32-1")
    match.estado = MatchStatus.LIVE
    match.goles_local = 0
    match.goles_visitante = 1
    db.commit()

    rows = svc.open_matches_for(user)
    row = next(r for r in rows if r["fifa_id"] == "KO-R32-1")
    assert row["can_submit"] is True
    assert row["requires_approval"] is True

    result = svc.submit(user, match.id, 2, 2)
    assert result["status"] == "pending_approval"

    matrix = svc.submission_matrix(fase=FASE_R32)
    participant_row = next(
        r for r in matrix["participants"] if r["participant_id"] == p.id
    )
    cell = next(c for c in participant_row["cells"] if c["match_id"] == match.id)
    assert cell["pending"] is True
    assert cell["request_id"] is not None
    assert cell["pending_pred_local"] == 2


def test_finished_match_without_late_allowed_is_closed(db, sample_participants):
    p = sample_participants[0]
    user = _participant_user(db, p)
    match = _knockout_match(db, fifa_id="KO-R32-2", kickoff_hours=-2)
    match.estado = MatchStatus.FINISHED
    db.commit()
    svc = PredictionSubmissionService(db)

    try:
        svc.submit(user, match.id, 1, 0)
        assert False, "debía fallar"
    except PredictionSubmissionError as exc:
        assert exc.code == "closed"


def test_late_submission_pending_and_admin_approve(db, sample_participants):
    p = sample_participants[0]
    user = _participant_user(db, p)
    admin = AuthService(db).register(
        email="admin2@test.com",
        nombre="Admin2",
        password="secret1",
        role=UserRole.ADMIN,
    )
    match = _knockout_match(db, fifa_id="KO-R32-2", kickoff_hours=-1)
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


def test_knockout_advance_r32_from_official_json(db):
    """Publica dieciseisavos desde el cuadro oficial JSON."""
    svc = KnockoutService(db)
    result = svc.advance_round_of_32()
    assert result["created"] == 16
    assert len(svc.matches.list(fase=FASE_R32)) == 16

    first = svc.matches.get_by_fifa_id("KO-R32-1")
    assert first is not None
    assert first.local == "Sudáfrica"
    assert first.visitante == "Canadá"

    again = svc.advance_round_of_32()
    assert again["created"] == 0


def test_knockout_sync_updates_existing(db):
    svc = KnockoutService(db)
    svc.advance_round_of_32()
    m = svc.matches.get_by_fifa_id("KO-R32-1")
    m.local = "Equipo X"
    svc.db.commit()

    result = svc.sync_r32_schedule()
    assert result["updated"] >= 1
    m2 = svc.matches.get_by_fifa_id("KO-R32-1")
    assert m2.local == "Sudáfrica"


def test_grace_day_first_match(db, sample_participants, monkeypatch):
    """KO-R32-1 acepta predicción todo el 28-jun-2026 hora Colombia."""
    from datetime import datetime
    from zoneinfo import ZoneInfo

    p = sample_participants[0]
    user = _participant_user(db, p)
    svc = PredictionSubmissionService(db)
    ko = KnockoutService(db)
    ko.advance_round_of_32()
    match = ko.matches.get_by_fifa_id("KO-R32-1")

    # Simula que ya pasó la hora del partido pero sigue siendo 28-jun en Colombia
    fixed = datetime(2026, 6, 28, 20, 0, tzinfo=ZoneInfo("America/Bogota"))

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz == ZoneInfo("America/Bogota"):
                return fixed
            return datetime(2026, 6, 29, 1, 0, tzinfo=timezone.utc)

    import app.services.prediction_submission_service as pss

    monkeypatch.setattr(pss, "datetime", FixedDatetime)

    result = svc.submit(user, match.id, 1, 0)
    assert result["status"] == "submitted"


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
    assert "+00:00" in row["fecha"] or row["fecha"].endswith("Z")


def test_round_matches_colombia_date_netherlands(db, sample_participants):
    p = sample_participants[0]
    user = _participant_user(db, p)
    KnockoutService(db).advance_round_of_32()
    rows = PredictionSubmissionService(db).open_matches_for(user)
    ned = next(r for r in rows if r["fifa_id"] == "KO-R32-3")
    assert ned["fecha_dia_colombia"] == "2026-06-29"
    assert ned["hora_colombia"] == "20:00"
