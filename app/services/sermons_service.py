"""Sermon service implementations for CRUD, passages, and suggestions."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import Select

from app.db.models import BibleVerses, SermonPassages, Sermons
from app.schemas.sermons import (
    PatchedSermon,
    PatchedSermonPassage,
    Sermon,
    SermonPassage,
    SermonSuggestionsResponse,
)
from app.services._mappers import sermon_passage_schema, sermon_schema
from app.services._reference import format_ref, parse_reference


def _sermon_with_relations_stmt() -> Select:
    """Build a base sermon select statement with relations eagerly loaded."""
    return select(Sermons).options(
        joinedload(Sermons.attachments),
        joinedload(Sermons.sermon_passages)
        .joinedload(SermonPassages.start_verse)
        .joinedload(BibleVerses.book),
        joinedload(Sermons.sermon_passages)
        .joinedload(SermonPassages.end_verse)
        .joinedload(BibleVerses.book),
    )


def _get_sermon_or_404(
    db: Session, sermon_id: int, *, with_relations: bool = False
) -> Sermons:
    """Load a sermon row by id or raise a 404 error."""
    if with_relations:
        sermon = (
            db.scalars(
                _sermon_with_relations_stmt().where(Sermons.sermon_id == sermon_id)
            )
            .unique()
            .first()
        )
    else:
        sermon = db.scalar(select(Sermons).where(Sermons.sermon_id == sermon_id))
    if sermon is None:
        raise HTTPException(status_code=404, detail="Sermon not found.")
    return sermon


def _get_passage_or_404(db: Session, sermon_id: int, passage_id: int) -> SermonPassages:
    """Load a sermon passage scoped to a sermon or raise 404."""
    passage = db.scalar(
        select(SermonPassages)
        .where(SermonPassages.sermon_id == sermon_id, SermonPassages.id == passage_id)
        .options(
            joinedload(SermonPassages.start_verse).joinedload(BibleVerses.book),
            joinedload(SermonPassages.end_verse).joinedload(BibleVerses.book),
        )
    )
    if passage is None:
        raise HTTPException(status_code=404, detail="Sermon passage not found.")
    return passage


def _coerce_sermon_fields(
    payload: Sermon | PatchedSermon, existing: Sermons | None = None
) -> dict:
    """Extract writable sermon fields from schema payloads."""
    data = payload.model_dump(exclude_unset=True)
    writable_keys = {
        "preached_on",
        "title",
        "speaker_name",
        "series_name",
        "location_name",
        "notes_md",
    }
    cleaned = {k: v for k, v in data.items() if k in writable_keys}
    if existing is None:
        if not cleaned.get("title"):
            raise HTTPException(status_code=400, detail="title is required.")
        cleaned["preached_on"] = cleaned.get("preached_on") or date.today()
    else:
        if "title" in cleaned and not cleaned["title"]:
            raise HTTPException(status_code=400, detail="title cannot be blank.")
        if "preached_on" in cleaned and cleaned["preached_on"] is None:
            cleaned["preached_on"] = existing.preached_on
    return cleaned


def _resolve_passage_verse_ids(
    db: Session, payload: SermonPassage | PatchedSermonPassage
) -> tuple[int | None, int | None, str | None]:
    """Resolve passage verse ids from payload fields and optional `ref_text`."""
    ref_text = payload.ref_text.strip() if payload.ref_text else None
    if ref_text:
        try:
            start_v, end_v = parse_reference(db, ref_text)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        normalized = format_ref(start_v, end_v)
        end_id = end_v.verse_id if end_v.verse_id != start_v.verse_id else None
        return start_v.verse_id, end_id, normalized

    start_id = payload.start_verse_id
    end_id = payload.end_verse_id
    if start_id is None:
        return None, None, ref_text

    start_v = db.scalar(
        select(BibleVerses)
        .where(BibleVerses.verse_id == start_id)
        .options(joinedload(BibleVerses.book))
    )
    if start_v is None:
        raise HTTPException(status_code=400, detail="start_verse_id is invalid.")

    end_v = None
    if end_id is not None:
        end_v = db.scalar(
            select(BibleVerses)
            .where(BibleVerses.verse_id == end_id)
            .options(joinedload(BibleVerses.book))
        )
        if end_v is None:
            raise HTTPException(status_code=400, detail="end_verse_id is invalid.")
    normalized = format_ref(start_v, end_v or start_v)
    return start_id, end_id, normalized


def list_sermons(db: Session, q: str | None = None) -> list[Sermon]:
    """Return sermons ordered by newest preached date, optionally filtered by title."""
    stmt = _sermon_with_relations_stmt().order_by(
        Sermons.preached_on.desc(), Sermons.sermon_id.desc()
    )
    query = (q or "").strip()
    if query:
        stmt = stmt.where(Sermons.title.ilike(f"%{query}%"))
    sermons = db.scalars(stmt).unique().all()
    return [sermon_schema(row, include_nested=True) for row in sermons]


def create_sermon(db: Session, payload: Sermon) -> Sermon:
    """Create and return a sermon record from the supplied payload."""
    values = _coerce_sermon_fields(payload)
    sermon = Sermons(**values)
    db.add(sermon)
    db.commit()
    return get_sermon(db, sermon.sermon_id)


def get_sermon(db: Session, sermon_id: int) -> Sermon:
    """Fetch a sermon by id with related passages and attachments."""
    sermon = _get_sermon_or_404(db, sermon_id, with_relations=True)
    return sermon_schema(sermon, include_nested=True)


def update_sermon(db: Session, sermon_id: int, payload: Sermon) -> Sermon:
    """Fully update a sermon's writable fields and return the updated row."""
    sermon = _get_sermon_or_404(db, sermon_id)
    values = _coerce_sermon_fields(payload, sermon)
    if "title" not in values:
        raise HTTPException(status_code=400, detail="title is required.")
    for key in (
        "preached_on",
        "title",
        "speaker_name",
        "series_name",
        "location_name",
        "notes_md",
    ):
        setattr(sermon, key, values.get(key))
    db.commit()
    return get_sermon(db, sermon_id)


def patch_sermon(db: Session, sermon_id: int, payload: PatchedSermon) -> Sermon:
    """Partially update a sermon's writable fields and return the updated row."""
    sermon = _get_sermon_or_404(db, sermon_id)
    values = _coerce_sermon_fields(payload, sermon)
    for key, value in values.items():
        setattr(sermon, key, value)
    db.commit()
    return get_sermon(db, sermon_id)


def delete_sermon(db: Session, sermon_id: int) -> None:
    """Delete a sermon by id."""
    sermon = _get_sermon_or_404(db, sermon_id)
    db.delete(sermon)
    db.commit()


def list_sermon_passages(db: Session, sermon_id: int) -> list[SermonPassage]:
    """List passages for a sermon ordered by `ord` then `id`."""
    _get_sermon_or_404(db, sermon_id)
    passages = db.scalars(
        select(SermonPassages)
        .where(SermonPassages.sermon_id == sermon_id)
        .options(
            joinedload(SermonPassages.start_verse).joinedload(BibleVerses.book),
            joinedload(SermonPassages.end_verse).joinedload(BibleVerses.book),
        )
        .order_by(SermonPassages.ord, SermonPassages.id)
    ).all()
    return [sermon_passage_schema(row) for row in passages]


def create_sermon_passage(
    db: Session, sermon_id: int, payload: SermonPassage
) -> SermonPassage:
    """Create a sermon passage, deriving verse ids from `ref_text` when provided."""
    _get_sermon_or_404(db, sermon_id)
    start_id, end_id, normalized_ref = _resolve_passage_verse_ids(db, payload)
    if start_id is None:
        raise HTTPException(
            status_code=400, detail="start_verse_id or ref_text is required."
        )

    max_ord = (
        db.scalar(
            select(func.max(SermonPassages.ord)).where(
                SermonPassages.sermon_id == sermon_id
            )
        )
        or 0
    )
    passage = SermonPassages(
        sermon_id=sermon_id,
        start_verse_id=start_id,
        end_verse_id=end_id,
        ref_text=normalized_ref,
        context_note=payload.context_note,
        ord=max_ord + 1,
    )
    db.add(passage)
    db.commit()
    return get_sermon_passage(db, sermon_id, passage.id)


def get_sermon_passage(db: Session, sermon_id: int, passage_id: int) -> SermonPassage:
    """Fetch one sermon passage by sermon id and passage id."""
    passage = _get_passage_or_404(db, sermon_id, passage_id)
    return sermon_passage_schema(passage)


def update_sermon_passage(
    db: Session,
    sermon_id: int,
    passage_id: int,
    payload: SermonPassage,
) -> SermonPassage:
    """Fully update a sermon passage and return the updated passage."""
    passage = _get_passage_or_404(db, sermon_id, passage_id)
    start_id, end_id, normalized_ref = _resolve_passage_verse_ids(db, payload)
    if start_id is None:
        raise HTTPException(
            status_code=400, detail="start_verse_id or ref_text is required."
        )

    passage.start_verse_id = start_id
    passage.end_verse_id = end_id
    passage.ref_text = normalized_ref
    passage.context_note = payload.context_note
    db.commit()
    return get_sermon_passage(db, sermon_id, passage_id)


def patch_sermon_passage(
    db: Session,
    sermon_id: int,
    passage_id: int,
    payload: PatchedSermonPassage,
) -> SermonPassage:
    """Partially update a sermon passage and return the updated passage."""
    passage = _get_passage_or_404(db, sermon_id, passage_id)
    values = payload.model_dump(exclude_unset=True)

    if any(key in values for key in {"ref_text", "start_verse_id", "end_verse_id"}):
        start_id, end_id, normalized_ref = _resolve_passage_verse_ids(db, payload)
        if start_id is not None:
            passage.start_verse_id = start_id
            passage.end_verse_id = end_id
            passage.ref_text = normalized_ref

    if "context_note" in values:
        passage.context_note = payload.context_note

    db.commit()
    return get_sermon_passage(db, sermon_id, passage_id)


def delete_sermon_passage(db: Session, sermon_id: int, passage_id: int) -> None:
    """Delete a sermon passage scoped to the given sermon."""
    passage = _get_passage_or_404(db, sermon_id, passage_id)
    db.delete(passage)
    db.commit()


def _distinct_recent_values(db: Session, column) -> list[str]:
    """Return non-empty distinct column values ordered by most recent sermon date."""
    rows = db.execute(
        select(column, func.max(Sermons.preached_on).label("latest"))
        .where(column.is_not(None), column != "")
        .group_by(column)
        .order_by(func.max(Sermons.preached_on).desc())
    ).all()
    return [row[0] for row in rows if row[0]]


def get_suggestions(db: Session) -> SermonSuggestionsResponse:
    """Return distinct speaker, series, and location name suggestions."""
    return SermonSuggestionsResponse(
        speakers=_distinct_recent_values(db, Sermons.speaker_name),
        series=_distinct_recent_values(db, Sermons.series_name),
        locations=_distinct_recent_values(db, Sermons.location_name),
    )
