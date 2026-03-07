from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth_placeholder
from app.schemas.search import ReferenceSearchResponse, SermonSearchResponse, VerseSearchResponse
from app.services import search_service

router = APIRouter(tags=["search"], dependencies=[Depends(require_auth_placeholder)])


@router.get("/", response_model=VerseSearchResponse, operation_id="search_retrieve")
def search_retrieve(
    q: str = Query(..., description="Free-text query to search for within verse text."),
    book: str | None = Query(default=None),
    chapter: int | None = Query(default=None),
    exact: bool = Query(default=False),
    page: int = Query(default=1),
    testament: str | None = Query(default=None),
    translation: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> VerseSearchResponse:
    return search_service.search_verses(
        db=db,
        q=q,
        page=page,
        book=book,
        chapter=chapter,
        testament=testament,
        exact=exact,
        translation=translation,
    )


@router.get("/ref/", response_model=ReferenceSearchResponse, operation_id="search_ref_retrieve")
def search_ref_retrieve(
    q: str = Query(..., description='Reference string such as "John 3:16-18".'),
    db: Session = Depends(get_db),
) -> ReferenceSearchResponse:
    return search_service.resolve_reference(db=db, q=q)


@router.get("/sermons/", response_model=SermonSearchResponse, operation_id="search_sermons_retrieve")
def search_sermons_retrieve(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SermonSearchResponse:
    return search_service.search_sermons(db=db, q=q)
