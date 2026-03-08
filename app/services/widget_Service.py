"""Widget service implementations for CRUD operations."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import BibleVerses, BibleWidgetVerses
from app.schemas.widget import BibleWidget, PartialBibleWidget
from app.services._mappers import widget_schema


def _widget_query():
    """Build the base widget select statement with verse relations loaded."""
    return select(BibleWidgetVerses).options(
        joinedload(BibleWidgetVerses.start_verse).joinedload(BibleVerses.book),
        joinedload(BibleWidgetVerses.end_verse).joinedload(BibleVerses.book),
    )


def _get_widget_or_404(db: Session, widget_id: int) -> BibleWidgetVerses:
    """Load one widget entry or raise a 404 error."""
    row = db.scalar(_widget_query().where(BibleWidgetVerses.id == widget_id))
    if row is None:
        raise HTTPException(status_code=404, detail="Widget entry not found.")
    return row


def _validate_verse_ids(db: Session, start_verse_id: int, end_verse_id: int) -> None:
    """Validate that start and end verse ids exist."""
    start_exists = db.scalar(
        select(BibleVerses.verse_id).where(BibleVerses.verse_id == start_verse_id)
    )
    end_exists = db.scalar(
        select(BibleVerses.verse_id).where(BibleVerses.verse_id == end_verse_id)
    )
    if start_exists is None or end_exists is None:
        raise HTTPException(
            status_code=400, detail="Invalid start_verse_id or end_verse_id."
        )


def list_widgets(db: Session) -> list[BibleWidget]:
    """List widget entries ordered by weight desc then reference."""
    rows = db.scalars(
        _widget_query().order_by(
            BibleWidgetVerses.weight.desc(), BibleWidgetVerses.ref.asc()
        )
    ).all()
    return [widget_schema(row) for row in rows]


def create_widget(db: Session, payload: BibleWidget) -> BibleWidget:
    """Create or update a widget entry for the same start/end/translation tuple."""
    if payload.start_verse_id is None or payload.end_verse_id is None:
        raise HTTPException(
            status_code=400, detail="start_verse_id and end_verse_id are required."
        )
    if not payload.translation or not payload.ref or not payload.display_text:
        raise HTTPException(
            status_code=400, detail="translation, ref, and display_text are required."
        )

    _validate_verse_ids(db, payload.start_verse_id, payload.end_verse_id)

    existing = db.scalar(
        _widget_query().where(
            BibleWidgetVerses.start_verse_id == payload.start_verse_id,
            BibleWidgetVerses.end_verse_id == payload.end_verse_id,
            BibleWidgetVerses.translation == payload.translation,
        )
    )

    if existing is None:
        existing = BibleWidgetVerses(
            start_verse_id=payload.start_verse_id,
            end_verse_id=payload.end_verse_id,
            translation=payload.translation,
            ref=payload.ref,
            display_text=payload.display_text,
            weight=payload.weight or 1,
        )
        db.add(existing)
    else:
        existing.ref = payload.ref
        existing.display_text = payload.display_text
        if payload.weight is not None:
            existing.weight = payload.weight

    db.commit()
    db.refresh(existing)
    return get_widget(db, existing.id)


def get_widget(db: Session, widget_id: int) -> BibleWidget:
    """Retrieve one widget entry by id."""
    return widget_schema(_get_widget_or_404(db, widget_id))


def update_widget(db: Session, widget_id: int, payload: BibleWidget) -> BibleWidget:
    """Fully update a widget entry's writable fields."""
    row = _get_widget_or_404(db, widget_id)
    if payload.start_verse_id is None or payload.end_verse_id is None:
        raise HTTPException(
            status_code=400, detail="start_verse_id and end_verse_id are required."
        )
    if not payload.translation or not payload.ref or not payload.display_text:
        raise HTTPException(
            status_code=400, detail="translation, ref, and display_text are required."
        )

    _validate_verse_ids(db, payload.start_verse_id, payload.end_verse_id)

    row.start_verse_id = payload.start_verse_id
    row.end_verse_id = payload.end_verse_id
    row.translation = payload.translation
    row.ref = payload.ref
    row.display_text = payload.display_text
    row.weight = payload.weight or row.weight
    db.commit()
    return get_widget(db, widget_id)


def patch_widget(
    db: Session, widget_id: int, payload: PartialBibleWidget
) -> BibleWidget:
    """Partially update a widget entry's writable fields."""
    row = _get_widget_or_404(db, widget_id)
    values = payload.model_dump(exclude_unset=True)

    start_id = values.get("start_verse_id", row.start_verse_id)
    end_id = values.get("end_verse_id", row.end_verse_id)
    _validate_verse_ids(db, start_id, end_id)

    for key, value in values.items():
        setattr(row, key, value)

    db.commit()
    return get_widget(db, widget_id)


def delete_widget(db: Session, widget_id: int) -> None:
    """Delete a widget entry by id."""
    row = _get_widget_or_404(db, widget_id)
    db.delete(row)
    db.commit()
