from app.schemas.base import APIModel


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


class AuthDetailResponse(APIModel):
    detail: str


class CsrfResponse(APIModel):
    detail: str
