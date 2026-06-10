"""Tests de integración de la API (endpoints)."""
from __future__ import annotations

import pytest

from app.models.match import Match, MatchStatus
from app.models.user import UserRole
from app.services.auth_service import AuthService


@pytest.fixture()
def admin_token(db, client):
    AuthService(db).register(
        email="admin@test.com", nombre="Admin", password="secret1", role=UserRole.ADMIN
    )
    resp = client.post(
        "/api/v1/auth/login", json={"email": "admin@test.com", "password": "secret1"}
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


@pytest.fixture()
def auth_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


def test_health(client):
    assert client.get("/health").json()["status"] == "healthy"


def test_root(client):
    assert client.get("/").json()["status"] == "ok"


def test_login_invalid(client):
    resp = client.post("/api/v1/auth/login", json={"email": "x@y.com", "password": "bad"})
    assert resp.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_returns_user(client, auth_headers):
    resp = client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "ADMIN"


def test_create_participant_public(client):
    # Modo single-user: crear participante no requiere autenticación
    resp = client.post("/api/v1/participants", json={"nombre": "Ana", "email": "a@a.com"})
    assert resp.status_code == 201


def test_participant_crud(client, auth_headers):
    create = client.post(
        "/api/v1/participants",
        json={"nombre": "Ana", "email": "ana@x.com"},
        headers=auth_headers,
    )
    assert create.status_code == 201
    pid = create.json()["id"]

    assert client.get("/api/v1/participants").status_code == 200
    assert client.get(f"/api/v1/participants/{pid}").json()["nombre"] == "Ana"

    upd = client.put(
        f"/api/v1/participants/{pid}", json={"nombre": "Ana M"}, headers=auth_headers
    )
    assert upd.json()["nombre"] == "Ana M"

    assert client.delete(f"/api/v1/participants/{pid}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/v1/participants/{pid}").status_code == 404


def test_duplicate_participant(client, auth_headers):
    client.post(
        "/api/v1/participants", json={"nombre": "Aaa", "email": "dup@x.com"}, headers=auth_headers
    )
    second = client.post(
        "/api/v1/participants", json={"nombre": "Bbb", "email": "dup@x.com"}, headers=auth_headers
    )
    assert second.status_code == 409


def test_match_result_flow(db, client, auth_headers):
    match = Match(fifa_id="M-1", local="X", visitante="Y", estado=MatchStatus.SCHEDULED)
    db.add(match)
    db.commit()

    participant = client.post(
        "/api/v1/participants", json={"nombre": "Ana", "email": "ana@x.com"}, headers=auth_headers
    ).json()

    pred = client.post(
        "/api/v1/predictions",
        json={
            "participant_id": participant["id"],
            "match_id": match.id,
            "pred_local": 2,
            "pred_visitante": 1,
        },
        headers=auth_headers,
    )
    assert pred.status_code == 201

    result = client.post(
        f"/api/v1/matches/{match.id}/result",
        json={"goles_local": 2, "goles_visitante": 1},
        headers=auth_headers,
    )
    assert result.status_code == 200
    assert result.json()["estado"] == "FINISHED"

    ranking = client.get("/api/v1/ranking").json()
    assert ranking[0]["puntos_totales"] == 5


def test_prediction_blocked_after_finish(db, client, auth_headers):
    match = Match(fifa_id="M-2", local="X", visitante="Y", estado=MatchStatus.FINISHED)
    db.add(match)
    db.commit()
    participant = client.post(
        "/api/v1/participants", json={"nombre": "Beto", "email": "b@x.com"}, headers=auth_headers
    ).json()

    resp = client.post(
        "/api/v1/predictions",
        json={
            "participant_id": participant["id"],
            "match_id": match.id,
            "pred_local": 1,
            "pred_visitante": 1,
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400


def test_dashboard_summary(client):
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    assert "total_partidos" in resp.json()


def test_admin_sync_public(client):
    # Modo single-user: la sincronización ya no requiere autenticación
    assert client.post("/api/v1/admin/sync").status_code == 200


def test_export_ranking(client):
    resp = client.get("/api/v1/export/ranking.xlsx")
    assert resp.status_code == 200
    assert "spreadsheet" in resp.headers["content-type"]


def test_export_pdf(client):
    resp = client.get("/api/v1/export/summary.pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
