from fastapi import APIRouter, Depends, Path, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_auth_placeholder
from app.schemas.verses import (
    PatchedVerseNote,
    VerseCommentaryResponse,
    VerseCrossReferencesResponse,
    VerseIntentResponse,
    VerseNote,
    VerseSermonResponse,
)
from app.services import verses_service

router = APIRouter(tags=["verses"], dependencies=[Depends(require_auth_placeholder)])


@router.get("/", response_model=VerseIntentResponse, operation_id="verses_retrieve")
def verses_retrieve(
    query: str = Query(..., description='Bible reference such as "John 3:16-18".'),
    translation: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> VerseIntentResponse:
    return verses_service.get_passage_or_intent(db=db, query=query, translation=translation)


@router.get("/commentaries/", response_model=VerseCommentaryResponse, operation_id="verses_commentaries_retrieve")
def verses_commentaries_retrieve(
    ref: str = Query(...),
    db: Session = Depends(get_db),
) -> VerseCommentaryResponse:
    return verses_service.get_commentaries(db=db, ref=ref)


@router.get("/crossrefs/", response_model=VerseCrossReferencesResponse, operation_id="verses_crossrefs_retrieve")
def verses_crossrefs_retrieve(
    ref: str = Query(...),
    db: Session = Depends(get_db),
) -> VerseCrossReferencesResponse:
    return verses_service.get_cross_references(db=db, ref=ref)


@router.get("/notes/", response_model=list[VerseNote], operation_id="verses_notes_list")
def verses_notes_list(
    verse_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[VerseNote]:
    return verses_service.list_notes(db=db, verse_id=verse_id)


@router.post("/notes/", response_model=VerseNote, status_code=status.HTTP_201_CREATED, operation_id="verses_notes_create")
def verses_notes_create(payload: VerseNote, db: Session = Depends(get_db)) -> VerseNote:
    return verses_service.create_note(db=db, payload=payload)


@router.get("/notes/{note_id}/", response_model=VerseNote, operation_id="verses_notes_retrieve")
def verses_notes_retrieve(
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> VerseNote:
    return verses_service.get_note(db=db, note_id=note_id)


@router.put("/notes/{note_id}/", response_model=VerseNote, operation_id="verses_notes_update")
def verses_notes_update(
    payload: VerseNote,
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> VerseNote:
    return verses_service.update_note(db=db, note_id=note_id, payload=payload)


@router.patch("/notes/{note_id}/", response_model=VerseNote, operation_id="verses_notes_partial_update")
def verses_notes_partial_update(
    payload: PatchedVerseNote,
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> VerseNote:
    return verses_service.patch_note(db=db, note_id=note_id, payload=payload)


@router.delete("/notes/{note_id}/", status_code=status.HTTP_204_NO_CONTENT, operation_id="verses_notes_destroy")
def verses_notes_destroy(
    note_id: int = Path(...),
    db: Session = Depends(get_db),
) -> None:
    verses_service.delete_note(db=db, note_id=note_id)


@router.get("/sermons/", response_model=VerseSermonResponse, operation_id="verses_sermons_retrieve")
def verses_sermons_retrieve(
    ref: str = Query(...),
    db: Session = Depends(get_db),
) -> VerseSermonResponse:
    return verses_service.get_sermons_for_reference(db=db, ref=ref)
