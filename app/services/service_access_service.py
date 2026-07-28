"""Staff-managed service identities and non-expiring read-only tokens."""

from __future__ import annotations

import secrets

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ApiAccessTokens, ApiUsers, ApiUsersAccountType
from app.services.auth_service import _token_hash, _utcnow
from sermon_archive.schemas import (
    ServiceAccountCreateRequest,
    ServiceAccountResponse,
    ServiceAccountUpdateRequest,
    ServiceTokenCreateRequest,
    ServiceTokenCreatedResponse,
    ServiceTokenResponse,
)

_READ_SCOPE = "archive:read"


def _account_response(db: Session, account: ApiUsers) -> ServiceAccountResponse:
    token_count = db.scalar(
        select(func.count())
        .select_from(ApiAccessTokens)
        .where(ApiAccessTokens.user_id == account.user_id)
    )
    return ServiceAccountResponse(
        id=account.user_id,
        name=account.username,
        is_active=bool(account.is_active),
        created_at=account.created_at,
        token_count=token_count or 0,
    )


def _token_response(token: ApiAccessTokens) -> ServiceTokenResponse:
    return ServiceTokenResponse(
        id=token.token_id,
        name=token.token_name or "",
        created_at=token.created_at,
        last_used_at=token.last_used_at,
        revoked_at=token.revoked_at,
        scope=_READ_SCOPE,
    )


def _service_account(db: Session, account_id: int) -> ApiUsers:
    account = db.scalar(
        select(ApiUsers).where(
            ApiUsers.user_id == account_id,
            ApiUsers.account_type == ApiUsersAccountType.SERVICE,
        )
    )
    if account is None:
        raise HTTPException(status_code=404, detail="Service account not found.")
    return account


def list_accounts(db: Session) -> list[ServiceAccountResponse]:
    accounts = db.scalars(
        select(ApiUsers)
        .where(ApiUsers.account_type == ApiUsersAccountType.SERVICE)
        .order_by(func.lower(ApiUsers.username), ApiUsers.user_id)
    ).all()
    return [_account_response(db, account) for account in accounts]


def create_account(
    db: Session, payload: ServiceAccountCreateRequest
) -> ServiceAccountResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Service account name is required.")
    account = ApiUsers(
        username=name,
        password_hash=None,
        email=None,
        account_type=ApiUsersAccountType.SERVICE,
        is_active=1,
        is_staff=0,
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="That service account name is already in use."
        ) from exc
    db.refresh(account)
    return _account_response(db, account)


def update_account(
    db: Session, account_id: int, payload: ServiceAccountUpdateRequest
) -> ServiceAccountResponse:
    account = _service_account(db, account_id)
    account.is_active = 1 if payload.is_active else 0
    db.commit()
    db.refresh(account)
    return _account_response(db, account)


def list_tokens(db: Session, account_id: int) -> list[ServiceTokenResponse]:
    _service_account(db, account_id)
    tokens = db.scalars(
        select(ApiAccessTokens)
        .where(ApiAccessTokens.user_id == account_id)
        .order_by(ApiAccessTokens.created_at.desc(), ApiAccessTokens.token_id.desc())
    ).all()
    return [_token_response(token) for token in tokens]


def create_token(
    db: Session, account_id: int, payload: ServiceTokenCreateRequest
) -> ServiceTokenCreatedResponse:
    account = _service_account(db, account_id)
    if not account.is_active:
        raise HTTPException(
            status_code=400, detail="Activate the service account before creating a token."
        )
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Token name is required.")
    raw_token = secrets.token_urlsafe(48)
    token = ApiAccessTokens(
        user_id=account.user_id,
        token_hash=_token_hash(raw_token),
        token_name=name,
        expires_at=None,
        last_used_at=None,
        scopes=_READ_SCOPE,
    )
    db.add(token)
    db.commit()
    db.refresh(token)
    metadata = _token_response(token)
    return ServiceTokenCreatedResponse(
        **metadata.model_dump(),
        access_token=raw_token,
    )


def revoke_token(db: Session, account_id: int, token_id: int) -> ServiceTokenResponse:
    _service_account(db, account_id)
    token = db.scalar(
        select(ApiAccessTokens).where(
            ApiAccessTokens.token_id == token_id,
            ApiAccessTokens.user_id == account_id,
        )
    )
    if token is None:
        raise HTTPException(status_code=404, detail="Service token not found.")
    if token.revoked_at is None:
        token.revoked_at = _utcnow()
        db.commit()
        db.refresh(token)
    return _token_response(token)
