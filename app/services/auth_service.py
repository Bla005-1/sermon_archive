"""Authentication service functions.

Current implementations are intentionally lightweight placeholders until real auth
(session or token based) is wired in.
"""

from fastapi import HTTPException, Request

from app.schemas.auth import CsrfResponse, LoginRequest, UserResponse


def _placeholder_user(username: str = "anonymous") -> UserResponse:
    """Build a predictable placeholder user payload for unauthenticated development."""
    return UserResponse(
        id=0,
        username=username,
        email="",
        first_name="",
        last_name="",
        is_active=True,
        is_staff=False,
    )


def get_csrf_payload(request: Request) -> CsrfResponse:
    """Return a placeholder CSRF response until cookie-based CSRF is implemented."""
    return CsrfResponse(detail="CSRF placeholder: cookie issuance not implemented yet.")


def login_user(request: Request, credentials: LoginRequest) -> UserResponse:
    """Validate login payload and return a placeholder user object."""
    if not credentials.username or not credentials.password:
        raise HTTPException(status_code=400, detail="Username and password are required.")
    return _placeholder_user(username=credentials.username)


def logout_user(request: Request) -> None:
    """Placeholder logout handler that will later clear session/cookies."""
    return None


def get_me(request: Request) -> UserResponse:
    """Return the currently resolved placeholder user payload."""
    username = getattr(getattr(request, "state", None), "username", None) or "anonymous"
    return _placeholder_user(username=username)


def refresh_user(request: Request) -> UserResponse:
    """Return refreshed placeholder user data for the current request."""
    username = getattr(getattr(request, "state", None), "username", None) or "anonymous"
    return _placeholder_user(username=username)
