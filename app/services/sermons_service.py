"""Sermon service implementations for CRUD and suggestions."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased, joinedload
from sqlalchemy.sql import Select

from app.db.models import (
    ApiUsers,
    BibleBooks,
    BibleVerses,
    ScriptureReferences,
    ScriptureReferencesSourceType,
    Sermons,
)
from app.services._mappers import sermon_schema
from app.services._reference import format_ref
from sermon_archive.schemas import (
    PatchedSermon,
    Sermon,
    SermonBrowseItem,
    SermonBrowseType,
    SermonSuggestionsResponse,
)


def _sermon_with_relations_stmt() -> Select:
    """Build a base sermon select statement with relations eagerly loaded."""
    return select(Sermons).options(
        joinedload(Sermons.sermon_attachments),
        joinedload(Sermons.user),
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


def _assert_can_write_sermon(current_user: ApiUsers, sermon: Sermons) -> None:
    """Allow sermon writes for the owner or staff users."""
    if bool(current_user.is_staff) or sermon.user_id == current_user.user_id:
        return
    raise HTTPException(status_code=403, detail="You cannot edit this sermon.")


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
        "notes_markdown",
    }
    cleaned = {key: value for key, value in data.items() if key in writable_keys}
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


def _apply_browse_filters(
    stmt: Select,
    *,
    year: int | None = None,
    speaker: str | None = None,
    series: str | None = None,
    location: str | None = None,
) -> Select:
    """Apply exact sermon browse filters to a select statement."""
    if year is not None:
        stmt = stmt.where(
            Sermons.preached_on >= date(year, 1, 1),
            Sermons.preached_on < date(year + 1, 1, 1),
        )
    if speaker is not None:
        stmt = stmt.where(Sermons.speaker_name == speaker)
    if series is not None:
        stmt = stmt.where(Sermons.series_name == series)
    if location is not None:
        stmt = stmt.where(Sermons.location_name == location)
    return stmt


def _sermon_browse_item(
    sermon: Sermons, *, order_number: int, reference: str | None = None
) -> SermonBrowseItem:
    """Build the compact sermon browse response shape."""
    return SermonBrowseItem(
        sermon_id=sermon.sermon_id,
        title=sermon.title,
        speaker_name=sermon.speaker_name,
        preached_on=sermon.preached_on,
        order_number=order_number,
        reference=reference,
    )


def browse_sermons(
    db: Session,
    *,
    browse_type: SermonBrowseType,
    year: int | None = None,
    speaker: str | None = None,
    series: str | None = None,
    location: str | None = None,
) -> list[SermonBrowseItem]:
    """Return compact sermon browse rows ordered by time or scripture position."""
    if browse_type == SermonBrowseType.time:
        stmt = _apply_browse_filters(
            select(Sermons).order_by(
                Sermons.preached_on.desc(),
                Sermons.sermon_id.desc(),
            ),
            year=year,
            speaker=speaker,
            series=series,
            location=location,
        )
        sermons = db.scalars(stmt).all()
        return [
            _sermon_browse_item(sermon, order_number=index)
            for index, sermon in enumerate(sermons, start=1)
        ]

    start_verse = aliased(BibleVerses)
    end_verse = aliased(BibleVerses)
    start_book = aliased(BibleBooks)
    end_book = aliased(BibleBooks)

    stmt = (
        select(Sermons, ScriptureReferences)
        .join(
            ScriptureReferences,
            ScriptureReferences.source_id == Sermons.sermon_id,
        )
        .join(start_verse, ScriptureReferences.start_verse_id == start_verse.verse_id)
        .join(start_book, start_verse.book_id == start_book.book_id)
        .outerjoin(end_verse, ScriptureReferences.end_verse_id == end_verse.verse_id)
        .outerjoin(end_book, end_verse.book_id == end_book.book_id)
        .where(ScriptureReferences.source_type == ScriptureReferencesSourceType.SERMON)
        .options(
            joinedload(ScriptureReferences.start_verse).joinedload(BibleVerses.book),
            joinedload(ScriptureReferences.end_verse).joinedload(BibleVerses.book),
        )
        .order_by(
            start_book.book_order,
            start_verse.chapter_number,
            start_verse.verse_number,
            func.coalesce(end_book.book_order, start_book.book_order),
            func.coalesce(end_verse.chapter_number, start_verse.chapter_number),
            func.coalesce(end_verse.verse_number, start_verse.verse_number),
            Sermons.preached_on.desc(),
            Sermons.sermon_id.desc(),
            ScriptureReferences.display_order,
            ScriptureReferences.scripture_reference_id,
        )
    )
    stmt = _apply_browse_filters(
        stmt,
        year=year,
        speaker=speaker,
        series=series,
        location=location,
    )
    rows = db.execute(stmt).all()

    items: list[SermonBrowseItem] = []
    for index, (sermon, scripture_ref) in enumerate(rows, start=1):
        end = scripture_ref.end_verse or scripture_ref.start_verse
        items.append(
            _sermon_browse_item(
                sermon,
                order_number=index,
                reference=scripture_ref.reference_text
                or format_ref(scripture_ref.start_verse, end),
            )
        )
    return items


def create_sermon(db: Session, payload: Sermon, current_user: ApiUsers) -> Sermon:
    """Create and return a sermon record from the supplied payload."""
    values = _coerce_sermon_fields(payload)
    sermon = Sermons(**values, user_id=current_user.user_id)
    db.add(sermon)
    db.commit()
    return get_sermon(db, sermon.sermon_id)


def get_sermon(db: Session, sermon_id: int) -> Sermon:
    """Fetch a sermon by id with related attachments."""
    sermon = _get_sermon_or_404(db, sermon_id, with_relations=True)
    return sermon_schema(sermon, include_nested=True)


def update_sermon(
    db: Session, sermon_id: int, payload: Sermon, current_user: ApiUsers
) -> Sermon:
    """Fully update a sermon's writable fields and return the updated row."""
    sermon = _get_sermon_or_404(db, sermon_id)
    _assert_can_write_sermon(current_user, sermon)
    values = _coerce_sermon_fields(payload, sermon)
    if "title" not in values:
        raise HTTPException(status_code=400, detail="title is required.")
    for key in (
        "preached_on",
        "title",
        "speaker_name",
        "series_name",
        "location_name",
        "notes_markdown",
    ):
        setattr(sermon, key, values.get(key))
    db.commit()
    return get_sermon(db, sermon_id)


def patch_sermon(
    db: Session, sermon_id: int, payload: PatchedSermon, current_user: ApiUsers
) -> Sermon:
    """Partially update a sermon's writable fields and return the updated row."""
    sermon = _get_sermon_or_404(db, sermon_id)
    _assert_can_write_sermon(current_user, sermon)
    values = _coerce_sermon_fields(payload, sermon)
    for key, value in values.items():
        setattr(sermon, key, value)
    db.commit()
    return get_sermon(db, sermon_id)


def delete_sermon(db: Session, sermon_id: int, current_user: ApiUsers) -> None:
    """Delete a sermon by id."""
    sermon = _get_sermon_or_404(db, sermon_id)
    _assert_can_write_sermon(current_user, sermon)
    db.delete(sermon)
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
