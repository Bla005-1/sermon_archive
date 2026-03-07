"""Search service implementations for verses, references, and sermons."""

from __future__ import annotations

import re
from collections import OrderedDict
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import BibleBooks, BibleVerses, Sermons, VerseTextsMarked
from app.schemas.search import (
    ReferenceSearchResponse,
    SermonSearchResponse,
    VerseSearchResponse,
    VerseSearchResponseTypeEnum,
    VerseSearchResult,
)
from app.services._mappers import bible_verse_schema, sermon_schema
from app.services._reference import format_ref, parse_reference


def _tokenize_search_terms(query: str) -> list[str]:
    """Split a free-text query into lower-cased word tokens."""
    return re.findall(r"[\w']+", query.lower())


def search_verses(
    db: Session,
    q: str,
    page: int = 1,
    book: str | None = None,
    chapter: int | None = None,
    testament: str | None = None,
    exact: bool = False,
    translation: str | None = None,
) -> VerseSearchResponse:
    """Search verse text rows with optional filters and paginated results."""
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Provide a search query in the 'q' query param.")

    page = max(page, 1)
    page_size = 20

    stmt = (
        select(VerseTextsMarked)
        .join(BibleVerses, VerseTextsMarked.verse_id == BibleVerses.verse_id)
        .join(BibleBooks, BibleBooks.book_id == BibleVerses.book_id)
        .options(joinedload(VerseTextsMarked.verse).joinedload(BibleVerses.book))
    )

    filters = []
    if translation:
        filters.append(func.upper(VerseTextsMarked.translation) == translation.strip().upper())
    if book:
        filters.append(func.lower(BibleBooks.name) == book.strip().lower())
    if chapter is not None:
        filters.append(BibleVerses.chapter == chapter)
    if testament and testament.strip().upper() in {"OT", "NT"}:
        filters.append(BibleBooks.testament == testament.strip().upper())

    if exact:
        filters.append(VerseTextsMarked.plain_text.ilike(f"%{query}%"))
    else:
        terms = _tokenize_search_terms(query)
        if not terms:
            raise HTTPException(status_code=400, detail="Provide a non-empty search query.")
        filters.append(and_(*[VerseTextsMarked.plain_text.ilike(f"%{term}%") for term in terms]))

    if filters:
        stmt = stmt.where(and_(*filters))

    stmt = stmt.order_by(
        BibleBooks.order_num,
        BibleVerses.chapter,
        BibleVerses.verse,
        func.lower(VerseTextsMarked.translation),
    )

    rows = db.scalars(stmt).all()

    selected_rows: Sequence[VerseTextsMarked]
    if translation:
        selected_rows = rows
    else:
        # Prefer ESV when multiple translations exist for the same verse.
        by_verse: OrderedDict[int, VerseTextsMarked] = OrderedDict()
        for row in rows:
            verse_id = row.verse_id
            current = by_verse.get(verse_id)
            if current is None:
                by_verse[verse_id] = row
                continue
            if current.translation.upper() != "ESV" and row.translation.upper() == "ESV":
                by_verse[verse_id] = row
        selected_rows = list(by_verse.values())

    total = len(selected_rows)
    offset = (page - 1) * page_size
    paged = selected_rows[offset: offset + page_size]

    results = []
    for idx, row in enumerate(paged, start=1):
        verse = row.verse
        results.append(
            VerseSearchResult(
                order_num=offset + idx,
                verse_id=verse.verse_id,
                reference=format_ref(verse, verse),
                book=verse.book.name,
                chapter=verse.chapter,
                verse=verse.verse,
                translation=row.translation,
                text=row.plain_text,
            )
        )

    return VerseSearchResponse(
        type=VerseSearchResponseTypeEnum.TEXT_RESULTS,
        query=query,
        page=page,
        total=total,
        results=results,
    )


def resolve_reference(db: Session, q: str) -> ReferenceSearchResponse:
    """Parse a Bible reference into canonical start/end verse payloads."""
    query = (q or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="Provide a reference in the 'q' query param.")

    try:
        start, end = parse_reference(db, query)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ReferenceSearchResponse(
        reference=format_ref(start, end),
        start=bible_verse_schema(start),
        end=bible_verse_schema(end),
    )


def search_sermons(db: Session, q: str | None = None) -> SermonSearchResponse:
    """Search sermons by title and return a short list ordered by newest first."""
    query = (q or "").strip()
    if not query:
        return SermonSearchResponse(sermons=[])

    stmt = (
        select(Sermons)
        .where(Sermons.title.ilike(f"%{query}%"))
        .order_by(Sermons.preached_on.desc(), Sermons.sermon_id.desc())
        .limit(10)
    )
    sermons = db.scalars(stmt).all()
    return SermonSearchResponse(sermons=[sermon_schema(row, include_nested=False) for row in sermons])
