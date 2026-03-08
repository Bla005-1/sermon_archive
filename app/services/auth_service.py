"""Authentication services for session-cookie and bearer-token auth."""

from __future__ import annotations

import datetime
import hashlib
import hmac
import secrets
from dataclasses import dataclass

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.db.models import ApiAccessTokens, ApiSessions, ApiUsers
from app.schemas.auth import (
    CsrfResponse,
    LoginRequest,
    TokenLoginRequest,
    TokenResponse,
    TokenRevokeResponse,
    UserResponse,
)


@dataclass(slots=True)
class AuthContext:
    """Authenticated request context derived from either session or bearer token."""

    user: ApiUsers
    method: str
    session: ApiSessions | None = None
    token: ApiAccessTokens | None = None


def _utcnow() -> datetime.datetime:
    """Return UTC now as a naive datetime for DB compatibility."""
    return datetime.datetime.utcnow()


def _password_hash(password: str) -> str:
    """Create an scrypt password hash string with embedded parameters and salt."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify plain password against stored hash (scrypt or legacy plain fallback)."""
    if stored_hash.startswith("scrypt$"):
        try:
            _, salt_hex, digest_hex = stored_hash.split("$", 2)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
            actual = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
            return hmac.compare_digest(actual, expected)
        except Exception:
            return False
    if stored_hash.startswith("plain$"):
        return hmac.compare_digest(password, stored_hash.split("$", 1)[1])
    return hmac.compare_digest(password, stored_hash)


def _token_hash(token: str) -> str:
    """Hash an opaque bearer token before persisting/looking it up in storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _to_user_response(user: ApiUsers) -> UserResponse:
    """Convert API user row into existing UserResponse schema."""
    return UserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email or "",
        first_name="",
        last_name="",
        is_active=bool(user.is_active),
        is_staff=bool(user.is_staff),
    )


def _set_session_cookie(response: Response, session_id: str) -> None:
    """Set the HTTP-only session cookie using current runtime cookie settings."""
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore
        path="/",
    )


def _set_csrf_cookie(response: Response, csrf_token: str) -> None:
    """Set a CSRF cookie for browser clients."""
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        max_age=settings.session_ttl_minutes * 60,
        httponly=False,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,  # type: ignore
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear auth cookies from client responses."""
    response.delete_cookie(settings.session_cookie_name, path="/")
    response.delete_cookie(settings.csrf_cookie_name, path="/")


def _extract_bearer_token(request: Request) -> str | None:
    """Extract bearer token value from Authorization header if present."""
    header = request.headers.get("Authorization", "")
    if not header or not header.lower().startswith("bearer "):
        return None
    token = header.split(" ", 1)[1].strip()
    return token or None


def _create_session(db: Session, user: ApiUsers, request: Request) -> ApiSessions:
    """Create and persist a new authenticated browser session row."""
    now = _utcnow()
    session = ApiSessions(
        session_id=secrets.token_urlsafe(48),
        user_id=user.user_id,
        csrf_token=secrets.token_urlsafe(32),
        expires_at=now + datetime.timedelta(minutes=settings.session_ttl_minutes),
        last_seen_at=now,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        is_revoked=0,
    )
    db.add(session)
    user.last_login_at = now
    db.commit()
    db.refresh(session)
    return session


def _authenticate_session(db: Session, session_id: str) -> AuthContext | None:
    """Authenticate and refresh a session-based login context."""
    now = _utcnow()
    session = db.scalar(
        select(ApiSessions).where(
            ApiSessions.session_id == session_id,
            ApiSessions.is_revoked == 0,
            ApiSessions.expires_at > now,
        )
    )
    if session is None:
        return None

    user = db.scalar(
        select(ApiUsers).where(ApiUsers.user_id == session.user_id, ApiUsers.is_active == 1)
    )
    if user is None:
        return None

    session.last_seen_at = now
    db.commit()
    return AuthContext(user=user, method="session", session=session)


def _authenticate_token(db: Session, raw_token: str) -> AuthContext | None:
    """Authenticate and refresh a bearer-token login context."""
    now = _utcnow()
    token = db.scalar(
        select(ApiAccessTokens).where(
            ApiAccessTokens.token_hash == _token_hash(raw_token),
            ApiAccessTokens.revoked_at.is_(None),
            ApiAccessTokens.expires_at > now,
        )
    )
    if token is None:
        return None

    user = db.scalar(
        select(ApiUsers).where(ApiUsers.user_id == token.user_id, ApiUsers.is_active == 1)
    )
    if user is None:
        return None

    token.last_used_at = now
    db.commit()
    return AuthContext(user=user, method="token", token=token)


def authenticate_request(db: Session, request: Request) -> AuthContext | None:
    """Authenticate request via bearer token first, then fallback session cookie."""
    bearer = _extract_bearer_token(request)
    if bearer:
        context = _authenticate_token(db, bearer)
        if context:
            return context

    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        context = _authenticate_session(db, session_id)
        if context:
            return context

    return None


def require_authenticated_context(db: Session, request: Request) -> AuthContext:
    """Require a valid auth context or raise 401."""
    context = authenticate_request(db, request)
    if context is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return context


def get_csrf_payload(response: Response) -> CsrfResponse:
    """Issue a CSRF cookie for unauthenticated clients."""
    csrf_token = secrets.token_urlsafe(32)
    _set_csrf_cookie(response, csrf_token)
    return CsrfResponse(detail="CSRF cookie set.")


def login_user(db: Session, request: Request, response: Response, credentials: LoginRequest) -> UserResponse:
    """Authenticate username/password and establish a new session-cookie login."""
    username = (credentials.username or "").strip()
    password = credentials.password or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    user = db.scalar(
        select(ApiUsers).where(func.lower(ApiUsers.username) == username.lower(), ApiUsers.is_active == 1)
    )
    if user is None or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials.")

    session = _create_session(db, user, request)
    _set_session_cookie(response, session.session_id)
    _set_csrf_cookie(response, session.csrf_token)
    return _to_user_response(user)


def issue_token(db: Session, request: Request, payload: TokenLoginRequest) -> TokenResponse:
    """Authenticate credentials and issue a new bearer token record."""
    username = (payload.username or "").strip()
    password = payload.password or ""
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password are required.")

    user = db.scalar(
        select(ApiUsers).where(func.lower(ApiUsers.username) == username.lower(), ApiUsers.is_active == 1)
    )
    if user is None or not _verify_password(password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials.")

    raw_token = secrets.token_urlsafe(48)
    now = _utcnow()
    token = ApiAccessTokens(
        user_id=user.user_id,
        token_hash=_token_hash(raw_token),
        token_name=payload.token_name,
        expires_at=now + datetime.timedelta(minutes=settings.token_ttl_minutes),
        last_used_at=now,
    )
    user.last_login_at = now
    db.add(token)
    db.commit()

    return TokenResponse(
        access_token=raw_token,
        token_type="bearer",
        expires_at=token.expires_at,
    )


def revoke_token(db: Session, request: Request) -> TokenRevokeResponse:
    """Revoke the currently supplied bearer token."""
    raw_token = _extract_bearer_token(request)
    if not raw_token:
        raise HTTPException(status_code=400, detail="Bearer token required.")

    token = db.scalar(
        select(ApiAccessTokens).where(
            ApiAccessTokens.token_hash == _token_hash(raw_token),
            ApiAccessTokens.revoked_at.is_(None),
        )
    )
    if token is None:
        raise HTTPException(status_code=404, detail="Token not found.")

    token.revoked_at = _utcnow()
    db.commit()
    return TokenRevokeResponse(detail="Token revoked.")


def logout_user(db: Session, request: Request, response: Response) -> None:
    """Revoke current session and clear auth cookies."""
    session_id = request.cookies.get(settings.session_cookie_name)
    if session_id:
        session = db.scalar(select(ApiSessions).where(ApiSessions.session_id == session_id, ApiSessions.is_revoked == 0))
        if session is not None:
            session.is_revoked = 1
            db.commit()
    _clear_auth_cookies(response)


def get_me(db: Session, request: Request) -> UserResponse:
    """Return the authenticated user profile for the current request."""
    context = require_authenticated_context(db, request)
    return _to_user_response(context.user)


def refresh_user(db: Session, request: Request, response: Response) -> UserResponse:
    """Refresh active session expiry and return the current authenticated user."""
    context = require_authenticated_context(db, request)
    if context.session is not None:
        context.session.expires_at = _utcnow() + datetime.timedelta(minutes=settings.session_ttl_minutes)
        db.commit()
        _set_session_cookie(response, context.session.session_id)
        _set_csrf_cookie(response, context.session.csrf_token)
    return _to_user_response(context.user)


def ensure_bootstrap_admin(db: Session) -> None:
    """Create a bootstrap admin user from environment variables when configured."""
    username = settings.bootstrap_admin_username
    password = settings.bootstrap_admin_password
    if not username or not password:
        return

    existing = db.scalar(select(ApiUsers).where(func.lower(ApiUsers.username) == username.lower()))
    if existing is not None:
        return

    user = ApiUsers(
        username=username,
        email=None,
        password_hash=_password_hash(password),
        is_active=1,
        is_staff=1,
    )
    db.add(user)
    db.commit()
