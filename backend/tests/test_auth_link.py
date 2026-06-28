"""Tests de vinculación usuario ↔ participante."""
from __future__ import annotations

from app.models.participant import Participant
from app.models.user import UserRole
from app.services.auth_service import AuthService


def test_admin_linked_by_nombre(db):
    part = Participant(
        nombre="German Andres Bello Garcia",
        email="german.andres.bello.garcia@mundial2026.com",
    )
    db.add(part)
    db.commit()

    admin = AuthService(db).register(
        email="germandres_91@hotmail.com",
        nombre="German Andres Bello Garcia",
        password="secret1",
        role=UserRole.ADMIN,
    )
    assert admin.participant_id is None
    assert AuthService(db).link_user_to_participant(admin) is True
    assert admin.participant_id == part.id


def test_me_auto_links(db, client):
    part = Participant(nombre="Ana Test", email="ana@test.com")
    db.add(part)
    db.commit()
    AuthService(db).register(
        email="ana@test.com",
        nombre="Ana Test",
        password="secret1",
        role=UserRole.PARTICIPANT,
    )
    login = client.post("/api/v1/auth/login", json={"email": "ana@test.com", "password": "secret1"})
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["participant_id"] == part.id
