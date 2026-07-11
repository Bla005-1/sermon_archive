from __future__ import annotations

from sqlalchemy import select

from app.db.models import ApiUsers
from app.services import auth_service
from tests.factories import seed_token, seed_user


STAFF_HEADERS = {"X-Test-Is-Staff": "true"}


def test_users_admin_crud_lite(client, db_session):
    seed_user(db_session, staff=True)

    created = client.post(
        "/api/users",
        headers=STAFF_HEADERS,
        json={
            "username": "new-user",
            "email": "new-user@example.test",
            "password": "secret",
            "is_active": True,
            "is_staff": False,
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["username"] == "new-user"
    assert body["sermon_count"] == 0

    listed = client.get("/api/users", headers=STAFF_HEADERS, params={"q": "new"})
    assert listed.status_code == 200
    assert [item["username"] for item in listed.json()] == ["new-user"]

    updated = client.patch(
        f"/api/users/{body['id']}",
        headers=STAFF_HEADERS,
        json={"email": "updated@example.test", "is_active": False},
    )
    assert updated.status_code == 200
    assert updated.json()["email"] == "updated@example.test"
    assert updated.json()["is_active"] is False

    reset = client.post(
        f"/api/users/{body['id']}/password",
        headers=STAFF_HEADERS,
        json={"password": "new-secret"},
    )
    assert reset.status_code == 200
    user = db_session.scalar(
        select(ApiUsers).where(ApiUsers.username == "new-user")
    )
    assert user is not None
    assert user.password_hash.startswith("scrypt$")


def test_users_admin_routes_require_staff(client, db_session):
    seed_user(db_session, staff=False)

    response = client.get("/api/users")

    assert response.status_code == 403
    assert response.json()["detail"] == "Staff access required."


def test_users_reject_self_deactivation_and_duplicate_identity(client, db_session):
    seed_user(db_session, staff=True)
    seed_user(
        db_session,
        user_id=2,
        username="other",
        email="other@example.test",
    )

    self_update = client.patch(
        "/api/users/1",
        headers=STAFF_HEADERS,
        json={"is_active": False},
    )
    assert self_update.status_code == 400
    assert self_update.json()["detail"] == "You cannot deactivate your own user."

    duplicate = client.patch(
        "/api/users/2",
        headers=STAFF_HEADERS,
        json={"username": "reader"},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Username or email is already in use."


def test_current_user_can_update_profile_and_change_password(
    client, db_session, monkeypatch
):
    seed_user(db_session)
    raw_token = "plain-test-token"
    seed_token(db_session, auth_service._token_hash(raw_token))
    monkeypatch.setattr(
        auth_service,
        "_verify_password",
        lambda password, _hash: password == "old",
    )

    profile = client.patch(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"username": "updated-reader", "email": "updated@example.test"},
    )
    assert profile.status_code == 200
    assert profile.json()["username"] == "updated-reader"

    wrong = client.post(
        "/api/auth/me/password",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"current_password": "wrong", "new_password": "new"},
    )
    assert wrong.status_code == 400
    assert wrong.json()["detail"] == "Current password is incorrect."

    changed = client.post(
        "/api/auth/me/password",
        headers={"Authorization": f"Bearer {raw_token}"},
        json={"current_password": "old", "new_password": "new"},
    )
    assert changed.status_code == 200
    assert changed.json()["username"] == "updated-reader"
