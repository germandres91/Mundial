"""Fixtures compartidas para los tests."""
from __future__ import annotations

import os
import tempfile

# Motor "real" de la app durante los tests: archivo temporal aislado.
_TMP_DB = os.path.join(tempfile.gettempdir(), "mundial_test_app.db")
if os.path.exists(_TMP_DB):
    os.remove(_TMP_DB)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB}"
os.environ.setdefault("FOOTBALL_PROVIDER", "mock")
os.environ["SYNC_ENABLED"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.models.match import Match, MatchStatus  # noqa: E402
from app.models.participant import Participant  # noqa: E402
from app.models.user import UserRole  # noqa: E402
from app.services.auth_service import AuthService  # noqa: E402


@pytest.fixture()
def engine():
    eng = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)


@pytest.fixture()
def db(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine):
    from app.main import app

    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


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


@pytest.fixture()
def sample_participants(db):
    p1 = Participant(nombre="Ana", email="ana@test.com")
    p2 = Participant(nombre="Beto", email="beto@test.com")
    db.add_all([p1, p2])
    db.commit()
    return [p1, p2]


@pytest.fixture()
def sample_match(db):
    match = Match(
        fifa_id="T-1",
        grupo="A",
        fase="Fase de grupos",
        local="México",
        visitante="Brasil",
        estado=MatchStatus.SCHEDULED,
    )
    db.add(match)
    db.commit()
    return match
