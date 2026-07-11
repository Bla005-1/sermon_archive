from fastapi import APIRouter, Depends, Path, Query, Request, status
from sqlalchemy.orm import Session

from app.db.models import ApiUsers
from app.dependencies import get_db, require_auth
from app.services import user_service
from sermon_archive.schemas import (
    UserCreateRequest,
    UserDetailResponse,
    UserPasswordResetRequest,
    UserSummary,
    UserUpdateRequest,
)

router = APIRouter(tags=["users"], dependencies=[Depends(require_auth)])


def _current_user(request: Request) -> ApiUsers:
    return request.state.current_user


@router.get("", response_model=list[UserSummary], operation_id="users_list")
def users_list(
    request: Request,
    q: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    is_staff: bool | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[UserSummary]:
    return user_service.list_users(
        db=db,
        current_user=_current_user(request),
        q=q,
        is_active=is_active,
        is_staff=is_staff,
    )


@router.post(
    "",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="users_create",
)
def users_create(
    payload: UserCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    return user_service.create_user(
        db=db, current_user=_current_user(request), payload=payload
    )


@router.get(
    "/{user_id}", response_model=UserDetailResponse, operation_id="users_retrieve"
)
def users_retrieve(
    request: Request,
    user_id: int = Path(...),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    return user_service.get_user(
        db=db, current_user=_current_user(request), user_id=user_id
    )


@router.patch(
    "/{user_id}", response_model=UserDetailResponse, operation_id="users_partial_update"
)
def users_partial_update(
    payload: UserUpdateRequest,
    request: Request,
    user_id: int = Path(...),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    return user_service.update_user(
        db=db, current_user=_current_user(request), user_id=user_id, payload=payload
    )


@router.post(
    "/{user_id}/password",
    response_model=UserDetailResponse,
    operation_id="users_password_create",
)
def users_password_create(
    payload: UserPasswordResetRequest,
    request: Request,
    user_id: int = Path(...),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    return user_service.reset_user_password(
        db=db, current_user=_current_user(request), user_id=user_id, payload=payload
    )
