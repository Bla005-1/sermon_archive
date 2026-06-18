from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth
from sermon_archive.schemas import (
    PartialVerseNote,
    VerseCommentaryResponse,
    VerseCrossReferencesResponse,
    VerseLibraryItemReferenceResponse,
    VerseNote,
    VerseReferenceResponse,
    VerseSermonResponse,
    VerseTranslationsResponse,
)
from app.services import verses_service

router = APIRouter(tags=["verses"])


@router.get(
    "/reference",
    response_model=VerseReferenceResponse,
    operation_id="verses_reference_retrieve",
)
def verses_reference_retrieve(
    ref: str = Query(..., description="Bible reference to retrieve directly."),
    translation: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> VerseReferenceResponse:
    return verses_service.get_verse_by_reference(
        db=db,
        ref=ref,
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


@router.get(
    "/library-items",
    response_model=VerseLibraryItemReferenceResponse,
    operation_id="verses_library_items_retrieve",
    dependencies=[Depends(require_auth)],
)
def verses_library_items_retrieve(
    ref: str = Query(...),
    db: Session = Depends(get_db),
) -> VerseLibraryItemReferenceResponse:
    return verses_service.get_library_items_for_reference(db=db, ref=ref)
