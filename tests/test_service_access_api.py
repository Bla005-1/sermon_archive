from __future__ import annotations

from sqlalchemy import select

from app.db.models import ApiAccessTokens, ApiUsers, ApiUsersAccountType
from app.services import auth_service
from tests.factories import seed_user

STAFF_HEADERS = {"X-Test-Is-Staff": "true"}


def test_staff_manages_service_account_and_one_time_token(client, db_session):
    seed_user(db_session, staff=True)

    created = client.post(
        "/api/service-accounts",
        headers=STAFF_HEADERS,
        json={"name": "sermon-search"},
    )
    assert created.status_code == 201
    account = created.json()
    assert account["name"] == "sermon-search"
    assert account["is_active"] is True

    service_user = db_session.scalar(
        select(ApiUsers).where(ApiUsers.user_id == account["id"])
    )
    assert service_user is not None
    assert service_user.account_type == ApiUsersAccountType.SERVICE
    assert service_user.password_hash is None
    assert service_user.is_staff == 0

    token_created = client.post(
        f"/api/service-accounts/{account['id']}/tokens",
        headers=STAFF_HEADERS,
        json={"name": "production"},
    )
    assert token_created.status_code == 201
    token_body = token_created.json()
    assert token_body["access_token"]
    assert token_body["scope"] == "archive:read"

    stored = db_session.scalar(select(ApiAccessTokens))
    assert stored is not None
    assert stored.token_hash == auth_service._token_hash(token_body["access_token"])
    assert stored.expires_at is None
    assert stored.scopes == "archive:read"

    listed = client.get(
        f"/api/service-accounts/{account['id']}/tokens",
        headers=STAFF_HEADERS,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "production"
    assert "access_token" not in listed.json()[0]

    revoked = client.post(
        f"/api/service-accounts/{account['id']}/tokens/{token_body['id']}/revoke",
        headers=STAFF_HEADERS,
    )
    assert revoked.status_code == 200
    assert revoked.json()["revoked_at"] is not None


def test_service_access_requires_staff(client, db_session):
    seed_user(db_session, staff=False)

    response = client.get("/api/service-accounts")

    assert response.status_code == 403


def test_deactivated_service_cannot_create_tokens(client, db_session):
    seed_user(db_session, staff=True)
    created = client.post(
        "/api/service-accounts",
        headers=STAFF_HEADERS,
        json={"name": "disabled-service"},
    ).json()
    disabled = client.patch(
        f"/api/service-accounts/{created['id']}",
        headers=STAFF_HEADERS,
        json={"is_active": False},
    )
    assert disabled.status_code == 200

    token = client.post(
        f"/api/service-accounts/{created['id']}/tokens",
        headers=STAFF_HEADERS,
        json={"name": "should-fail"},
    )
    assert token.status_code == 400
