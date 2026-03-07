from fastapi import APIRouter, Request, Response, status

from app.schemas.auth import CsrfResponse, LoginRequest, UserResponse
from app.services import auth_service

router = APIRouter(tags=["auth"])


@router.get("/csrf/", response_model=CsrfResponse, operation_id="auth_csrf_retrieve")
def auth_csrf_retrieve(request: Request) -> CsrfResponse:
    return auth_service.get_csrf_payload(request=request)


@router.post("/login/", response_model=UserResponse, operation_id="auth_login_create")
def auth_login_create(payload: LoginRequest, request: Request) -> UserResponse:
    return auth_service.login_user(request=request, credentials=payload)


@router.post("/logout/", status_code=status.HTTP_200_OK, operation_id="auth_logout_create")
def auth_logout_create(request: Request) -> Response:
    auth_service.logout_user(request=request)
    return Response(status_code=status.HTTP_200_OK)


@router.get("/me/", response_model=UserResponse, operation_id="auth_me_retrieve")
def auth_me_retrieve(request: Request) -> UserResponse:
    return auth_service.get_me(request=request)


@router.get("/refresh/", response_model=UserResponse, operation_id="auth_refresh_retrieve")
def auth_refresh_retrieve(request: Request) -> UserResponse:
    return auth_service.refresh_user(request=request)
