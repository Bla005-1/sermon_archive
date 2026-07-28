"""User profile and staff user-management services."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import ApiUsers, ApiUsersAccountType, Sermons
from app.services import auth_service
from app.services._mappers import user_summary_schema
from sermon_archive.schemas import (
    CurrentUserPasswordRequest,
    CurrentUserUpdateRequest,
    UserCreateRequest,
    UserDetailResponse,
    UserPasswordResetRequest,
    UserResponse,
    UserSummary,
    UserUpdateRequest,
)


def _to_user_response(user: ApiUsers) -> UserResponse:
    return UserResponse(
        id=user.user_id,
        username=user.username,
        email=user.email or "",
        first_name="",
        last_name="",
        is_active=bool(user.is_active),
        is_staff=bool(user.is_staff),
    )


def _clean_username(value: str | None) -> str:
    username = (value or "").strip()
    if not username:
        raise HTTPException(status_code=400, detail="username is required.")
    return username


def _clean_email(value: str | None) -> str | None:
    email = (value or "").strip()
    return email or None


def _clean_password(value: str | None) -> str:
    password = value or ""
    if not password:
        raise HTTPException(status_code=400, detail="password is required.")
    return password


def _require_staff(current_user: ApiUsers) -> None:
    if (
        current_user.account_type != ApiUsersAccountType.HUMAN
        or not bool(current_user.is_staff)
    ):
        raise HTTPException(status_code=403, detail="Staff access required.")


def _get_user_or_404(db: Session, user_id: int) -> ApiUsers:
    user = db.scalar(
        select(ApiUsers).where(
            ApiUsers.user_id == user_id,
            ApiUsers.account_type == ApiUsersAccountType.HUMAN,
        )
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


def _commit_user_change(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Username or email is already in use.",
        ) from exc


def _user_detail(db: Session, user: ApiUsers) -> UserDetailResponse:
    sermon_count = (
        db.scalar(
            select(func.count())
            .select_from(Sermons)
            .where(Sermons.user_id == user.user_id)
        )
        or 0
    )
    return UserDetailResponse(
        **user_summary_schema(user).model_dump(),
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
        sermon_count=sermon_count,
    )


def list_users(
    db: Session,
    *,
    current_user: ApiUsers,
    q: str | None = None,
    is_active: bool | None = None,
    is_staff: bool | None = None,
) -> list[UserSummary]:
    _require_staff(current_user)
    stmt = (
        select(ApiUsers)
        .where(ApiUsers.account_type == ApiUsersAccountType.HUMAN)
        .order_by(func.lower(ApiUsers.username), ApiUsers.user_id)
    )
    query = (q or "").strip()
    if query:
        like = f"%{query.lower()}%"
        stmt = stmt.where(
            (func.lower(ApiUsers.username).like(like))
            | (func.lower(ApiUsers.email).like(like))
        )
    if is_active is not None:
        stmt = stmt.where(ApiUsers.is_active == (1 if is_active else 0))
    if is_staff is not None:
        stmt = stmt.where(ApiUsers.is_staff == (1 if is_staff else 0))
    return [user_summary_schema(user) for user in db.scalars(stmt).all()]


def create_user(
    db: Session, *, current_user: ApiUsers, payload: UserCreateRequest
) -> UserDetailResponse:
    _require_staff(current_user)
    user = ApiUsers(
        username=_clean_username(payload.username),
        email=_clean_email(payload.email),
        password_hash=auth_service._password_hash(_clean_password(payload.password)),
        account_type=ApiUsersAccountType.HUMAN,
        is_active=1 if payload.is_active else 0,
        is_staff=1 if payload.is_staff else 0,
    )
    db.add(user)
    _commit_user_change(db)
    db.refresh(user)
    return _user_detail(db, user)


def get_user(
    db: Session, *, current_user: ApiUsers, user_id: int
) -> UserDetailResponse:
    _require_staff(current_user)
    return _user_detail(db, _get_user_or_404(db, user_id))


def update_user(
    db: Session,
    *,
    current_user: ApiUsers,
    user_id: int,
    payload: UserUpdateRequest,
) -> UserDetailResponse:
    _require_staff(current_user)
    user = _get_user_or_404(db, user_id)
    values = payload.model_dump(exclude_unset=True)
    if "username" in values:
        user.username = _clean_username(values["username"])
    if "email" in values:
        user.email = _clean_email(values["email"])
    if "is_active" in values:
        if user.user_id == current_user.user_id and values["is_active"] is False:
            raise HTTPException(
                status_code=400, detail="You cannot deactivate your own user."
            )
        user.is_active = 1 if values["is_active"] else 0
    if "is_staff" in values:
        if user.user_id == current_user.user_id and values["is_staff"] is False:
            raise HTTPException(
                status_code=400, detail="You cannot remove your own staff access."
            )
        user.is_staff = 1 if values["is_staff"] else 0
    _commit_user_change(db)
    db.refresh(user)
    return _user_detail(db, user)


def reset_user_password(
    db: Session,
    *,
    current_user: ApiUsers,
    user_id: int,
    payload: UserPasswordResetRequest,
) -> UserDetailResponse:
    _require_staff(current_user)
    user = _get_user_or_404(db, user_id)
    user.password_hash = auth_service._password_hash(_clean_password(payload.password))
    _commit_user_change(db)
    db.refresh(user)
    return _user_detail(db, user)


def update_current_user(
    db: Session, *, current_user: ApiUsers, payload: CurrentUserUpdateRequest
) -> UserResponse:
    values = payload.model_dump(exclude_unset=True)
    if "username" in values:
        current_user.username = _clean_username(values["username"])
    if "email" in values:
        current_user.email = _clean_email(values["email"])
    _commit_user_change(db)
    db.refresh(current_user)
    return _to_user_response(current_user)


def change_current_user_password(
    db: Session, *, current_user: ApiUsers, payload: CurrentUserPasswordRequest
) -> UserResponse:
    if not auth_service._verify_password(
        payload.current_password or "", current_user.password_hash
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    current_user.password_hash = auth_service._password_hash(
        _clean_password(payload.new_password)
    )
    _commit_user_change(db)
    db.refresh(current_user)
    return _to_user_response(current_user)
