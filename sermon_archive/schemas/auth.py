import datetime as dt
from typing import Literal

from sermon_archive.schemas.base import APIModel


class LoginRequest(APIModel):
    username: str
    password: str


class UserResponse(APIModel):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_active: bool
    is_staff: bool


class UserSummary(APIModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_staff: bool


class UserCreateRequest(APIModel):
    username: str
    password: str
    email: str | None = None
    is_active: bool = True
    is_staff: bool = False


class UserUpdateRequest(APIModel):
    username: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_staff: bool | None = None


class UserDetailResponse(UserSummary):
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None
    last_login_at: dt.datetime | None = None
    sermon_count: int = 0


class UserPasswordResetRequest(APIModel):
    password: str


class CurrentUserUpdateRequest(APIModel):
    username: str | None = None
    email: str | None = None


class CurrentUserPasswordRequest(APIModel):
    current_password: str
    new_password: str


class AuthDetailResponse(APIModel):
    detail: str


class CsrfResponse(APIModel):
    detail: str


class ServiceAccountCreateRequest(APIModel):
    name: str


class ServiceAccountResponse(APIModel):
    id: int
    name: str
    is_active: bool
    created_at: dt.datetime | None = None
    token_count: int = 0


class ServiceAccountUpdateRequest(APIModel):
    is_active: bool


class ServiceTokenCreateRequest(APIModel):
    name: str


class ServiceTokenResponse(APIModel):
    id: int
    name: str
    created_at: dt.datetime | None = None
    last_used_at: dt.datetime | None = None
    revoked_at: dt.datetime | None = None
    scope: Literal["archive:read"] = "archive:read"


class ServiceTokenCreatedResponse(ServiceTokenResponse):
    access_token: str
