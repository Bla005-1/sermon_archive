"""Staff-only service account and token management routes."""

from fastapi import APIRouter, Depends, Path, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_staff
from app.services import service_access_service
from sermon_archive.schemas import (
    ServiceAccountCreateRequest,
    ServiceAccountResponse,
    ServiceAccountUpdateRequest,
    ServiceTokenCreateRequest,
    ServiceTokenCreatedResponse,
    ServiceTokenResponse,
)

router = APIRouter(
    tags=["service-access"],
    dependencies=[Depends(require_staff)],
)


@router.get("", response_model=list[ServiceAccountResponse])
def service_accounts_list(db: Session = Depends(get_db)) -> list[ServiceAccountResponse]:
    return service_access_service.list_accounts(db)


@router.post(
    "",
    response_model=ServiceAccountResponse,
    status_code=status.HTTP_201_CREATED,
)
def service_accounts_create(
    payload: ServiceAccountCreateRequest,
    db: Session = Depends(get_db),
) -> ServiceAccountResponse:
    return service_access_service.create_account(db, payload)


@router.patch("/{account_id}", response_model=ServiceAccountResponse)
def service_accounts_update(
    payload: ServiceAccountUpdateRequest,
    account_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ServiceAccountResponse:
    return service_access_service.update_account(db, account_id, payload)


@router.get(
    "/{account_id}/tokens",
    response_model=list[ServiceTokenResponse],
)
def service_tokens_list(
    account_id: int = Path(...),
    db: Session = Depends(get_db),
) -> list[ServiceTokenResponse]:
    return service_access_service.list_tokens(db, account_id)


@router.post(
    "/{account_id}/tokens",
    response_model=ServiceTokenCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
def service_tokens_create(
    payload: ServiceTokenCreateRequest,
    account_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ServiceTokenCreatedResponse:
    return service_access_service.create_token(db, account_id, payload)


@router.post(
    "/{account_id}/tokens/{token_id}/revoke",
    response_model=ServiceTokenResponse,
)
def service_tokens_revoke(
    account_id: int = Path(...),
    token_id: int = Path(...),
    db: Session = Depends(get_db),
) -> ServiceTokenResponse:
    return service_access_service.revoke_token(db, account_id, token_id)
