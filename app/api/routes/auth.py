from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.auth import (
    CsrfResponse,
    LoginRequest,
    TokenLoginRequest,
    TokenResponse,
    TokenRevokeResponse,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.get("/csrf", response_model=CsrfResponse, operation_id="auth_csrf_retrieve")
def auth_csrf_retrieve(response: Response) -> CsrfResponse:
    """Issue CSRF cookie used by browser clients for authenticated write requests."""
    return auth_service.get_csrf_payload(response=response)


@router.post("/login", response_model=UserResponse, operation_id="auth_login_create")
def auth_login_create(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a cookie-authenticated session and set CSRF cookie/header token pair."""
    return auth_service.login_user(
        db=db, request=request, response=response, credentials=payload
    )


@router.post("/token", response_model=TokenResponse, operation_id="auth_token_create")
def auth_token_create(
    payload: TokenLoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return auth_service.issue_token(db=db, request=request, payload=payload)


@router.post(
    "/token/revoke",
    response_model=TokenRevokeResponse,
    operation_id="auth_token_revoke_create",
)
def auth_token_revoke_create(
    request: Request, db: Session = Depends(get_db)
) -> TokenRevokeResponse:
    return auth_service.revoke_token(db=db, request=request)


@router.post(
    "/logout", status_code=status.HTTP_200_OK, operation_id="auth_logout_create"
)
def auth_logout_create(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    """Logout current session; cookie-authenticated write calls must send X-CSRF-Token."""
    auth_service.logout_user(db=db, request=request, response=response)
    response.status_code = status.HTTP_200_OK
    return response


@router.get("/me", response_model=UserResponse, operation_id="auth_me_retrieve")
def auth_me_retrieve(request: Request, db: Session = Depends(get_db)) -> UserResponse:
    return auth_service.get_me(db=db, request=request)


@router.post(
    "/refresh", response_model=UserResponse, operation_id="auth_refresh_create"
)
def auth_refresh_create(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    return auth_service.refresh_user(db=db, request=request, response=response)
