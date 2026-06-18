"""Public backend search endpoint."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.services import search_service
from sermon_archive.schemas import SearchResponse

router = APIRouter(tags=["search"])


@router.get("", response_model=SearchResponse, operation_id="search_retrieve")
def search_retrieve(
    q: str = Query(..., description="Search query or Bible reference."),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    domains: list[str] | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SearchResponse:
    return search_service.search(
        db=db,
        q=q,
        limit=limit,
        offset=offset,
        domains=domains,
    )
