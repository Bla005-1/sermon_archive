from __future__ import annotations

from sqlalchemy import select

from app.db.models import ApiSessions
from app.services import auth_service
from tests.factories import seed_service_user, seed_token, seed_user


def test_csrf_sets_cookie(client):
    response = client.get("/api/auth/csrf")

    assert response.status_code == 200
    assert response.json() == {"detail": "CSRF cookie set."}
    assert "csrftoken" in response.cookies


def test_login_rejects_blank_credentials(client, db_session):
    seed_user(db_session)

    response = client.post("/api/auth/login", json={"username": " ", "password": ""})

    assert response.status_code == 400
    assert response.json()["detail"] == "Username and password are required."


def test_login_sets_session_and_csrf_cookies(client, db_session, monkeypatch):
    seed_user(db_session)
    monkeypatch.setattr(auth_service, "_verify_password", lambda *_args: True)

    response = client.post(
        "/api/auth/login",
        json={"username": "Reader", "password": "secret"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "reader"
    assert "sessionid" in response.cookies
    assert "csrftoken" in response.cookies

    session = db_session.scalar(select(ApiSessions))
    assert session is not None
    assert session.user_id == 1
    assert session.is_revoked == 0


def test_public_token_routes_are_removed(client):
    assert client.post("/api/auth/token", json={}).status_code == 404
    assert client.post("/api/auth/token/revoke").status_code == 404


def test_me_requires_real_auth_context(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_me_accepts_valid_bearer_token(client, db_session):
    seed_service_user(db_session)
    raw_token = "plain-test-token"
    seed_token(
        db_session,
        auth_service._token_hash(raw_token),
        user_id=2,
        non_expiring=True,
    )

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json()["username"] == "search-service"


def test_human_bearer_token_is_rejected(client, db_session):
    seed_user(db_session)
    raw_token = "human-token"
    seed_token(db_session, auth_service._token_hash(raw_token))

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 401


def test_service_account_cannot_log_in_with_password(
    client, db_session, monkeypatch
):
    seed_service_user(db_session)
    monkeypatch.setattr(auth_service, "_verify_password", lambda *_args: True)

    response = client.post(
        "/api/auth/login",
        json={"username": "search-service", "password": "secret"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid credentials."


def test_service_token_rejects_mutating_request(client, db_session):
    seed_service_user(db_session)
    raw_token = "service-token"
    seed_token(
        db_session,
        auth_service._token_hash(raw_token),
        user_id=2,
        non_expiring=True,
    )

    response = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"username": "changed"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Service tokens are read-only."
