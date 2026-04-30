from __future__ import annotations

from sqlalchemy import select

from app.db.models import ApiAccessTokens, ApiSessions
from app.services import auth_service
from tests.factories import seed_token, seed_user


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


def test_token_issue_and_revoke(client, db_session, monkeypatch):
    seed_user(db_session)
    monkeypatch.setattr(auth_service, "_verify_password", lambda *_args: True)

    issue_response = client.post(
        "/api/auth/token",
        json={"username": "reader", "password": "secret", "token_name": "ci"},
    )

    assert issue_response.status_code == 200
    body = issue_response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]

    stored_token = db_session.scalar(select(ApiAccessTokens))
    assert stored_token is not None
    assert stored_token.token_hash == auth_service._token_hash(body["access_token"])

    revoke_response = client.post(
        "/api/auth/token/revoke",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )

    assert revoke_response.status_code == 200
    assert revoke_response.json() == {"detail": "Token revoked."}
    db_session.refresh(stored_token)
    assert stored_token.revoked_at is not None


def test_token_revoke_requires_bearer_token(client):
    response = client.post("/api/auth/token/revoke")

    assert response.status_code == 400
    assert response.json()["detail"] == "Bearer token required."


def test_me_requires_real_auth_context(client):
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required."


def test_me_accepts_valid_bearer_token(client, db_session):
    seed_user(db_session)
    raw_token = "plain-test-token"
    seed_token(db_session, auth_service._token_hash(raw_token))

    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {raw_token}"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "reader@example.test"
