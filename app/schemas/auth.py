from datetime import datetime

from app.schemas.base import APIModel


class LoginRequest(APIModel):
    username: str
    password: str


class TokenLoginRequest(APIModel):
    username: str
    password: str
    token_name: str | None = None


class UserResponse(APIModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_staff: bool


class AuthDetailResponse(APIModel):
    detail: str


class CsrfResponse(APIModel):
    detail: str


class TokenResponse(APIModel):
    access_token: str
    token_type: str
    expires_at: datetime


class TokenRevokeResponse(APIModel):
    detail: str
