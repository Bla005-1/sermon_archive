from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.dependencies import get_db
from sermon_archive.schemas import (
    CsrfResponse,
    CurrentUserPasswordRequest,
    CurrentUserUpdateRequest,
    LoginRequest,
    UserResponse,
)
from app.services import auth_service, user_service

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


@router.patch("/me", response_model=UserResponse, operation_id="auth_me_partial_update")
def auth_me_partial_update(
    payload: CurrentUserUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> UserResponse:
    context = auth_service.require_authenticated_context(db=db, request=request)
    return user_service.update_current_user(
        db=db, current_user=context.user, payload=payload
    )


@router.post(
    "/me/password",
    response_model=UserResponse,
    operation_id="auth_me_password_create",
)
def auth_me_password_create(
    payload: CurrentUserPasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> UserResponse:
    context = auth_service.require_authenticated_context(db=db, request=request)
    return user_service.change_current_user_password(
        db=db, current_user=context.user, payload=payload
    )


@router.post(
    "/refresh", response_model=UserResponse, operation_id="auth_refresh_create"
)
def auth_refresh_create(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> UserResponse:
    return auth_service.refresh_user(db=db, request=request, response=response)
