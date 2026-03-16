from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from app.schemas.verses import (
    PartialVerseNote,
    VerseCommentaryResponse,
    VerseCrossReferencesResponse,
    VerseQueryResponse,
    VerseNote,
    VerseTextSearchResponse,
    VerseSermonResponse,
    VerseTranslationsResponse,
)
from app.services import verses_service

router = APIRouter(tags=["verses"])


@router.get("", response_model=VerseQueryResponse, operation_id="verses_lookup")
def verses_lookup(
    q: str = Query(
        ...,
        description=("Search by reference"),
    ),
    translation: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> VerseQueryResponse:
    return verses_service.resolve_query_intent(db=db, q=q, translation=translation)


@router.get(
    "/search",
    response_model=VerseTextSearchResponse,
    operation_id="verses_search_retrieve",
)
def verses_search_retrieve(
    q: str = Query(..., description="Free-text query to search within verse text."),
    book: str | None = Query(default=None),
    chapter: int | None = Query(default=None),
    exact: bool = Query(default=False),
    page: int = Query(default=1),
    testament: str | None = Query(default=None),
    translation: str | None = Query(default=None),
    db: Session = Depends(get_db),
    ) -> VerseTextSearchResponse:
    return verses_service.search_verse_text(
        db=db,
        q=q,
        page=page,
        book=book,
        chapter=chapter,
        testament=testament,
        exact=exact,
        translation=translation,
    )


@router.get(
    "/translations",
    response_model=VerseTranslationsResponse,
    operation_id="verses_translations_list",
)
def verses_translations_list(
    db: Session = Depends(get_db),
) -> VerseTranslationsResponse:
    return verses_service.list_translations(db=db)


@router.get(
    "/commentaries",
    response_model=VerseCommentaryResponse,
    operation_id="verses_commentaries_retrieve",
    dependencies=[Depends(require_auth)],
)
def verses_commentaries_retrieve(
    ref: str = Query(...),
    db: Session = Depends(get_db),
) -> VerseCommentaryResponse:
    return verses_service.get_commentaries(db=db, ref=ref)


@router.get(
    "/crossrefs",
    response_model=VerseCrossReferencesResponse,
    operation_id="verses_crossrefs_retrieve",
    dependencies=[Depends(require_auth)],
)
def verses_crossrefs_retrieve(
    ref: str = Query(...),
    db: Session = Depends(get_db),
) -> VerseCrossReferencesResponse:
    return verses_service.get_cross_references(db=db, ref=ref)


@router.get(
    "/notes",
    response_model=list[VerseNote],
    operation_id="verses_notes_list",
    dependencies=[Depends(require_auth)],
)
def verses_notes_list(
    verse_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[VerseNote]:
    return verses_service.list_notes(db=db, verse_id=verse_id)


@router.post(
    "/notes",
    response_model=VerseNote,
    status_code=status.HTTP_201_CREATED,
    operation_id="verses_notes_create",
    dependencies=[Depends(require_auth)],
)
def verses_notes_create(payload: VerseNote, db: Session = Depends(get_db)) -> VerseNote:
    return verses_service.create_note(db=db, payload=payload)


@router.get(
    "/notes/{note_id}",
    response_model=VerseNote,
    operation_id="verses_notes_retrieve",
    dependencies=[Depends(require_auth)],
)
def verses_notes_retrieve(
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> VerseNote:
    return verses_service.get_note(db=db, note_id=note_id)


@router.put(
    "/notes/{note_id}",
    response_model=VerseNote,
    operation_id="verses_notes_update",
    dependencies=[Depends(require_auth)],
)
def verses_notes_update(
    payload: VerseNote,
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> VerseNote:
    return verses_service.update_note(db=db, note_id=note_id, payload=payload)


@router.patch(
    "/notes/{note_id}",
    response_model=VerseNote,
    operation_id="verses_notes_partial_update",
    dependencies=[Depends(require_auth)],
)
def verses_notes_partial_update(
    payload: PartialVerseNote,
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> VerseNote:
    return verses_service.patch_note(db=db, note_id=note_id, payload=payload)


@router.delete(
    "/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="verses_notes_destroy",
    dependencies=[Depends(require_auth)],
)
def verses_notes_destroy(
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> None:
    verses_service.delete_note(db=db, note_id=note_id)


@router.get(
    "/sermons",
    response_model=VerseSermonResponse,
    operation_id="verses_sermons_retrieve",
    dependencies=[Depends(require_auth)],
)
def verses_sermons_retrieve(
    ref: str = Query(...),
    db: Session = Depends(get_db),
) -> VerseSermonResponse:
    return verses_service.get_sermons_for_reference(db=db, ref=ref)
