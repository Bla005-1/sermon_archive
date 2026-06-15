"""Sermon service implementations for CRUD and suggestions."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import Select

from app.db.models import Sermons
from app.services._mappers import sermon_schema
from sermon_archive.schemas import PatchedSermon, Sermon, SermonSuggestionsResponse


def _sermon_with_relations_stmt() -> Select:
    """Build a base sermon select statement with relations eagerly loaded."""
    return select(Sermons).options(joinedload(Sermons.sermon_attachments))


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


def create_sermon(db: Session, payload: Sermon) -> Sermon:
    """Create and return a sermon record from the supplied payload."""
    values = _coerce_sermon_fields(payload)
    sermon = Sermons(**values)
    db.add(sermon)
    db.commit()
    return get_sermon(db, sermon.sermon_id)


def get_sermon(db: Session, sermon_id: int) -> Sermon:
    """Fetch a sermon by id with related attachments."""
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
        "notes_markdown",
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
