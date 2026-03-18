"""Verse service implementations for passage intent, commentary, crossrefs, notes, and sermons."""

from __future__ import annotations

import re
from bisect import bisect_right
from functools import lru_cache
from typing import Any
from collections import OrderedDict
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    BibleBooks,
    BibleVerses,
    Commentaries,
    SermonPassages,
    VerseHeadings,
    VerseCrossrefs,
    VerseNotes,
    VerseTextsMarked,
)
from app.schemas.verses import (
    CommentaryEnd,
    CommentaryItem,
    CommentaryStart,
    CrossReferenceItem,
    CrossReferenceVerse,
    PartialVerseNote,
    VerseCommentaryResponse,
    VerseCrossReferencesResponse,
    VerseNavigationTarget,
    SearchIntentEnum,
    VerseQueryResponse,
    VerseNote,
    VerseTextSearchResponse,
    VerseTranslationsResponse,
    VerseSearchResult,
    VerseSermonItem,
    VerseSermonResponse,
)
from app.services._mappers import verse_note_schema
from app.services._reference import format_ref, parse_reference

SECTION_BOUNDARY_TRANSLATION = "ESV"
_section_start_id_cache: list[int] | None = None


def _load_verse_range(
    db: Session, start: BibleVerses, end: BibleVerses
) -> Sequence[BibleVerses]:
    """Load all verses between start and end verse ids."""
    lo = min(start.verse_id, end.verse_id)
    hi = max(start.verse_id, end.verse_id)
    return db.scalars(
        select(BibleVerses)
        .where(BibleVerses.verse_id >= lo, BibleVerses.verse_id <= hi)
        .options(joinedload(BibleVerses.book))
        .order_by(BibleVerses.verse_id)
    ).all()


def _preview_text_for_range(db: Session, start_id: int, end_id: int) -> str:
    """Build plain-text preview for a cross-reference verse range."""
    lo = min(start_id, end_id)
    hi = max(start_id, end_id)
    rows = db.scalars(
        select(VerseTextsMarked)
        .where(VerseTextsMarked.verse_id >= lo, VerseTextsMarked.verse_id <= hi)
        .order_by(VerseTextsMarked.verse_id, func.lower(VerseTextsMarked.translation))
    ).all()

    chosen_by_verse: dict[int, VerseTextsMarked] = {}
    for row in rows:
        current = chosen_by_verse.get(row.verse_id)
        if current is None:
            chosen_by_verse[row.verse_id] = row
            continue
        if current.translation.upper() != "ESV" and row.translation.upper() == "ESV":
            chosen_by_verse[row.verse_id] = row

    return " ".join(
        chosen_by_verse[key].plain_text for key in sorted(chosen_by_verse.keys())
    ).strip()


def _tokenize_search_terms(query: str) -> list[str]:
    """Split a free-text query into lower-cased word tokens."""
    return re.findall(r"[\w']+", query.lower())


def _verse_result_from_text_row(
    row: VerseTextsMarked, order_num: int, available_translations: Sequence[str] | None = None
) -> VerseSearchResult:
    verse = row.verse
    return VerseSearchResult(
        order_num=order_num,
        verse_id=verse.verse_id,
        reference=format_ref(verse, verse),
        book=verse.book.name,
        chapter=verse.chapter,
        verse=verse.verse,
        available_translations=list(available_translations or []),
        translation=row.translation,
        plain_text=row.plain_text,
        marked_text=row.marked_text,
        text=row.plain_text,
    )


def _available_translations_by_verse(
    rows: Sequence[VerseTextsMarked],
) -> dict[int, list[str]]:
    translations_by_verse: dict[int, list[str]] = {}
    for row in rows:
        values = translations_by_verse.setdefault(row.verse_id, [])
        if row.translation not in values:
            values.append(row.translation)
    return translations_by_verse


def _select_preferred_rows(rows: Sequence[VerseTextsMarked]) -> list[VerseTextsMarked]:
    """Keep one row per verse, preferring ESV when multiple translations exist."""
    by_verse: OrderedDict[int, VerseTextsMarked] = OrderedDict()
    for row in rows:
        verse_id = row.verse_id
        current = by_verse.get(verse_id)
        if current is None:
            by_verse[verse_id] = row
            continue
        if current.translation.upper() != "ESV" and row.translation.upper() == "ESV":
            by_verse[verse_id] = row
    return list(by_verse.values())


def _chapter_bounds(
    db: Session, verse: BibleVerses
) -> tuple[BibleVerses, BibleVerses] | None:
    verses = db.scalars(
        select(BibleVerses)
        .options(joinedload(BibleVerses.book))
        .where(BibleVerses.book_id == verse.book_id, BibleVerses.chapter == verse.chapter)
        .order_by(BibleVerses.verse_id)
    ).all()
    if not verses:
        return None
    return verses[0], verses[-1]


@lru_cache(maxsize=1)
def _cached_section_translation() -> str:
    return SECTION_BOUNDARY_TRANSLATION.upper()


def _section_start_ids(db: Session) -> list[int]:
    global _section_start_id_cache
    if _section_start_id_cache is not None:
        return _section_start_id_cache

    translation = _cached_section_translation()
    rows = db.scalars(
        select(VerseHeadings.start_verse_id)
        .where(func.upper(VerseHeadings.translation) == translation)
        .distinct()
        .order_by(VerseHeadings.start_verse_id)
    ).all()
    _section_start_id_cache = list(rows)
    return _section_start_id_cache


def _verse_by_id(db: Session, verse_id: int) -> BibleVerses | None:
    return db.scalar(
        select(BibleVerses)
        .options(joinedload(BibleVerses.book))
        .where(BibleVerses.verse_id == verse_id)
    )


def _first_verse_after(db: Session, verse_id: int) -> BibleVerses | None:
    return db.scalar(
        select(BibleVerses)
        .options(joinedload(BibleVerses.book))
        .where(BibleVerses.verse_id > verse_id)
        .order_by(BibleVerses.verse_id)
        .limit(1)
    )


def _last_verse_before(db: Session, verse_id: int) -> BibleVerses | None:
    return db.scalar(
        select(BibleVerses)
        .options(joinedload(BibleVerses.book))
        .where(BibleVerses.verse_id < verse_id)
        .order_by(desc(BibleVerses.verse_id))
        .limit(1)
    )


def _last_verse(db: Session) -> BibleVerses | None:
    return db.scalar(
        select(BibleVerses)
        .options(joinedload(BibleVerses.book))
        .order_by(desc(BibleVerses.verse_id))
        .limit(1)
    )


def _max_verse_before(db: Session, verse_id: int) -> BibleVerses | None:
    return db.scalar(
        select(BibleVerses)
        .options(joinedload(BibleVerses.book))
        .where(BibleVerses.verse_id < verse_id)
        .order_by(desc(BibleVerses.verse_id))
        .limit(1)
    )


def _nav_target(kind: str, start: BibleVerses, end: BibleVerses | None = None) -> VerseNavigationTarget:
    range_end = end or start
    reference = f"{start.book.name} {start.chapter}" if kind == "chapter" else format_ref(start, range_end)
    return VerseNavigationTarget(kind=kind, reference=reference, label=reference)


def _chapter_expand_target(verse: BibleVerses) -> VerseNavigationTarget:
    chapter_reference = f"{verse.book.name} {verse.chapter}"
    return VerseNavigationTarget(
        kind="chapter",
        reference=chapter_reference,
        label=chapter_reference,
    )


def _section_bounds_for_verse(
    db: Session, start: BibleVerses, end: BibleVerses
) -> tuple[BibleVerses, BibleVerses, int | None] | None:
    section_start_ids = _section_start_ids(db)
    if not section_start_ids:
        return None

    current_index = bisect_right(section_start_ids, start.verse_id) - 1
    if current_index < 0:
        return None

    section_start_id = section_start_ids[current_index]
    next_section_start_id = (
        section_start_ids[current_index + 1]
        if current_index + 1 < len(section_start_ids)
        else None
    )
    same_section = next_section_start_id is None or end.verse_id < next_section_start_id

    if next_section_start_id is None:
        section_end = _last_verse(db)
    else:
        section_end = _max_verse_before(db, next_section_start_id)

    section_start = _verse_by_id(db, section_start_id)
    if section_start is None or section_end is None or not same_section:
        return None

    return section_start, section_end, next_section_start_id


def _compute_expand_target(
    db: Session, start: BibleVerses, end: BibleVerses
) -> VerseNavigationTarget | None:
    chapter_bounds = _chapter_bounds(db, start)
    if chapter_bounds is None:
        return None

    chapter_start, chapter_end = chapter_bounds
    if start.verse_id == chapter_start.verse_id and end.verse_id == chapter_end.verse_id:
        return None

    section_bounds = _section_bounds_for_verse(db, start, end)
    if section_bounds is None:
        return _chapter_expand_target(start)

    section_start, section_end, _next_section_start_id = section_bounds
    query_matches_section = (
        start.verse_id == section_start.verse_id and end.verse_id == section_end.verse_id
    )

    if (
        query_matches_section
        or section_start.book_id != start.book_id
        or section_end.book_id != start.book_id
        or section_start.chapter != start.chapter
        or section_end.chapter != start.chapter
    ):
        return _chapter_expand_target(start)

    return _nav_target("section", section_start, section_end)


def _scope_for_range(
    db: Session, start: BibleVerses, end: BibleVerses, expand_target: VerseNavigationTarget | None
) -> str:
    chapter_bounds = _chapter_bounds(db, start)
    if chapter_bounds is not None:
        chapter_start, chapter_end = chapter_bounds
        if start.verse_id == chapter_start.verse_id and end.verse_id == chapter_end.verse_id:
            return "chapter"

    if start.verse_id == end.verse_id:
        return "verse"

    section_bounds = _section_bounds_for_verse(db, start, end)
    if section_bounds is not None:
        section_start, section_end, _ = section_bounds
        if start.verse_id == section_start.verse_id and end.verse_id == section_end.verse_id:
            return "section"

    if expand_target is not None:
        return expand_target.kind

    return "verse"


def _previous_target(
    db: Session, scope: str, start: BibleVerses, end: BibleVerses
) -> VerseNavigationTarget | None:
    if scope == "verse":
        previous_verse = _last_verse_before(db, start.verse_id)
        return _nav_target("verse", previous_verse) if previous_verse is not None else None

    if scope == "chapter":
        chapter_bounds = _chapter_bounds(db, start)
        if chapter_bounds is None:
            return None
        chapter_start, _chapter_end = chapter_bounds
        previous_verse = _last_verse_before(db, chapter_start.verse_id)
        if previous_verse is None:
            return None
        previous_bounds = _chapter_bounds(db, previous_verse)
        if previous_bounds is None:
            return None
        previous_start, previous_end = previous_bounds
        return _nav_target("chapter", previous_start, previous_end)

    if scope == "section":
        section_start_ids = _section_start_ids(db)
        current_index = bisect_right(section_start_ids, start.verse_id) - 1
        if current_index <= 0 or current_index >= len(section_start_ids):
            return None
        previous_start_id = section_start_ids[current_index - 1]
        current_start_id = section_start_ids[current_index]
        previous_start = _verse_by_id(db, previous_start_id)
        previous_end = _max_verse_before(db, current_start_id)
        if previous_start is None or previous_end is None:
            return None
        return _nav_target("section", previous_start, previous_end)

    return None


def _next_target(
    db: Session, scope: str, start: BibleVerses, end: BibleVerses
) -> VerseNavigationTarget | None:
    if scope == "verse":
        next_verse = _first_verse_after(db, end.verse_id)
        return _nav_target("verse", next_verse) if next_verse is not None else None

    if scope == "chapter":
        chapter_bounds = _chapter_bounds(db, start)
        if chapter_bounds is None:
            return None
        _chapter_start, chapter_end = chapter_bounds
        next_verse = _first_verse_after(db, chapter_end.verse_id)
        if next_verse is None:
            return None
        next_bounds = _chapter_bounds(db, next_verse)
        if next_bounds is None:
            return None
        next_start, next_end = next_bounds
        return _nav_target("chapter", next_start, next_end)

    if scope == "section":
        section_start_ids = _section_start_ids(db)
        current_index = bisect_right(section_start_ids, start.verse_id) - 1
        if current_index < 0 or current_index >= len(section_start_ids) - 1:
            return None
        next_start_id = section_start_ids[current_index + 1]
        next_next_start_id = (
            section_start_ids[current_index + 2]
            if current_index + 2 < len(section_start_ids)
            else None
        )
        next_start = _verse_by_id(db, next_start_id)
        next_end = _last_verse(db) if next_next_start_id is None else _max_verse_before(db, next_next_start_id)
        if next_start is None or next_end is None:
            return None
        return _nav_target("section", next_start, next_end)

    return None


def list_translations(db: Session) -> VerseTranslationsResponse:
    """Return distinct verse text translations in display order."""
    rows = db.scalars(
        select(VerseTextsMarked.translation)
        .where(VerseTextsMarked.translation.is_not(None), VerseTextsMarked.translation != "")
        .distinct()
        .order_by(func.lower(VerseTextsMarked.translation))
    ).all()
    return VerseTranslationsResponse(translations=list(rows))


def resolve_query_intent(
    db: Session,
    q: str,
    translation: str | None = None,
) -> VerseQueryResponse:
    """Resolve input as reference or text intent and return a single envelope."""
    query = (q or "").strip()
    if not query:
        raise HTTPException(
            status_code=400, detail="Provide a query in the 'q' query param."
        )

    try:
        start, end = parse_reference(db, query)
    except ValueError:
        return VerseQueryResponse(intent=SearchIntentEnum.TEXT, query=query)

    verses = _load_verse_range(db, start, end)
    verse_ids = [verse.verse_id for verse in verses]
    if not verse_ids:
        return VerseQueryResponse(
            intent=SearchIntentEnum.REFERENCE,
            query=format_ref(start, end),
            reference=format_ref(start, end),
            verses=[],
        )

    text_rows = db.scalars(
        select(VerseTextsMarked)
        .join(BibleVerses, VerseTextsMarked.verse_id == BibleVerses.verse_id)
        .options(joinedload(VerseTextsMarked.verse).joinedload(BibleVerses.book))
        .where(VerseTextsMarked.verse_id.in_(verse_ids))
        .order_by(BibleVerses.verse_id, func.lower(VerseTextsMarked.translation))
    ).all()
    available_translations = _available_translations_by_verse(text_rows)

    if translation:
        wanted = translation.strip().upper()
        picked_by_verse: OrderedDict[int, VerseTextsMarked] = OrderedDict()
        fallback_by_verse: OrderedDict[int, VerseTextsMarked] = OrderedDict()
        for row in text_rows:
            if row.verse_id not in fallback_by_verse:
                fallback_by_verse[row.verse_id] = row
            if row.translation.upper() == wanted:
                picked_by_verse[row.verse_id] = row
        selected = [
            picked_by_verse.get(vid, fallback_by_verse[vid])
            for vid in verse_ids
            if vid in fallback_by_verse
        ]
    else:
        selected = _select_preferred_rows(text_rows)

    expand_target = _compute_expand_target(db, start, end)
    scope = _scope_for_range(db, start, end, expand_target)
    return VerseQueryResponse(
        intent=SearchIntentEnum.REFERENCE,
        query=format_ref(start, end),
        reference=format_ref(start, end),
        scope=scope,
        previous_target=_previous_target(db, scope, start, end),
        expand_target=expand_target,
        next_target=_next_target(db, scope, start, end),
        verses=[
            _verse_result_from_text_row(
                row=row,
                order_num=idx,
                available_translations=available_translations.get(
                    row.verse_id, [row.translation]
                ),
            )
            for idx, row in enumerate(selected, start=1)
        ],
    )


def search_verse_text(
    db: Session,
    q: str,
    page: int = 1,
    book: str | None = None,
    chapter: int | None = None,
    testament: str | None = None,
    exact: bool = False,
    translation: str | None = None,
) -> VerseTextSearchResponse:
    """Search verse text rows with optional filters and paginated results."""
    query = (q or "").strip()
    if not query:
        raise HTTPException(
            status_code=400, detail="Provide a search query in the 'q' query param."
        )

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
        filters.append(
            func.upper(VerseTextsMarked.translation) == translation.strip().upper()
        )
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
            raise HTTPException(
                status_code=400, detail="Provide a non-empty search query."
            )
        filters.append(
            and_(*[VerseTextsMarked.plain_text.ilike(f"%{term}%") for term in terms])
        )

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
        selected_rows = _select_preferred_rows(rows)

    total = len(selected_rows)
    offset = (page - 1) * page_size
    paged = selected_rows[offset : offset + page_size]
    paged_verse_ids = [row.verse_id for row in paged]
    available_translations_by_verse: dict[int, list[str]] = {}
    if paged_verse_ids:
        translation_rows = db.scalars(
            select(VerseTextsMarked)
            .where(VerseTextsMarked.verse_id.in_(paged_verse_ids))
            .order_by(VerseTextsMarked.verse_id, func.lower(VerseTextsMarked.translation))
        ).all()
        available_translations_by_verse = _available_translations_by_verse(
            translation_rows
        )

    return VerseTextSearchResponse(
        query=query,
        page=page,
        total=total,
        results=[
            _verse_result_from_text_row(
                row=row,
                order_num=offset + idx,
                available_translations=available_translations_by_verse.get(
                    row.verse_id, [row.translation]
                ),
            )
            for idx, row in enumerate(paged, start=1)
        ],
    )


def get_commentaries(db: Session, ref: str) -> VerseCommentaryResponse:
    """Return commentary excerpts for verses resolved from a Bible reference."""
    reference = (ref or "").strip()
    if not reference:
        raise HTTPException(
            status_code=400, detail="Provide a reference in the 'ref' query param."
        )

    try:
        start, end = parse_reference(db, reference)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    verses = _load_verse_range(db, start, end)
    if not verses:
        return VerseCommentaryResponse(
            reference=format_ref(start, end), count=0, items=[]
        )

    lo = min(v.verse_id for v in verses)
    hi = max(v.verse_id for v in verses)
    book_ids = sorted({v.book_id for v in verses})

    rows = db.scalars(
        select(Commentaries)
        .where(
            Commentaries.start_verse_id <= hi,
            Commentaries.end_verse_id >= lo,
            Commentaries.book_id.in_(book_ids),
        )
        .options(
            joinedload(Commentaries.father),
            joinedload(Commentaries.start_verse).joinedload(BibleVerses.book),
            joinedload(Commentaries.end_verse).joinedload(BibleVerses.book),
            joinedload(Commentaries.book),
        )
        .order_by(
            Commentaries.start_verse_id,
            Commentaries.end_verse_id,
            Commentaries.commentary_id,
        )
    ).all()

    items: list[CommentaryItem] = []
    for row in rows:
        start_v = row.start_verse
        end_v = row.end_verse or row.start_verse
        if start_v.verse_id > end_v.verse_id:
            start_v, end_v = end_v, start_v

        father = row.father
        father_name = father.name if father else ""
        append = (row.append_to_author_name or "").strip()
        display_name = f"{father_name} {append}".strip() if append else father_name

        items.append(
            CommentaryItem(
                commentary_id=row.commentary_id,
                father_id=father.father_id if father else None,
                father_name=father_name,
                display_name=display_name,
                append_to_author_name=append,
                text=row.txt or "",
                book_id=row.book_id,
                start_verse_id=start_v.verse_id,
                end_verse_id=end_v.verse_id,
                reference=format_ref(start_v, end_v),
                source_url=row.source_url or "",
                source_title=row.source_title or "",
                default_year=father.default_year if father else None,
                wiki_url=father.wiki_url or "" if father else "",
                start=CommentaryStart(
                    book=start_v.book.name, chapter=start_v.chapter, verse=start_v.verse
                ),
                end=CommentaryEnd(
                    book=end_v.book.name, chapter=end_v.chapter, verse=end_v.verse
                ),
            )
        )

    return VerseCommentaryResponse(
        reference=format_ref(start, end), count=len(items), items=items
    )


def get_cross_references(db: Session, ref: str) -> VerseCrossReferencesResponse:
    """Return verse-level outbound cross references for a resolved reference range."""
    reference = (ref or "").strip()
    if not reference:
        raise HTTPException(
            status_code=400, detail="Provide a reference in the 'ref' query param."
        )

    try:
        start, end = parse_reference(db, reference)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    verses = _load_verse_range(db, start, end)
    verse_ids = [v.verse_id for v in verses]

    rows = db.scalars(
        select(VerseCrossrefs)
        .where(VerseCrossrefs.from_verse_id.in_(verse_ids) if verse_ids else False)  # type: ignore
        .options(
            joinedload(VerseCrossrefs.to_start_verse).joinedload(BibleVerses.book),
            joinedload(VerseCrossrefs.to_end_verse).joinedload(BibleVerses.book),
        )
        .order_by(
            VerseCrossrefs.from_verse_id, desc(VerseCrossrefs.votes), VerseCrossrefs.id
        )
    ).all()

    by_from: dict[int, list[VerseCrossrefs]] = {vid: [] for vid in verse_ids}
    for row in rows:
        by_from.setdefault(row.from_verse_id, []).append(row)

    payload: list[CrossReferenceVerse] = []
    for verse in verses:
        items: list[CrossReferenceItem] = []
        for row in by_from.get(verse.verse_id, []):
            to_start = row.to_start_verse
            to_end = row.to_end_verse or to_start
            items.append(
                CrossReferenceItem(
                    reference=format_ref(to_start, to_end),
                    votes=row.votes or 0,
                    note=row.note or "",
                    to_start_id=to_start.verse_id,
                    to_end_id=to_end.verse_id,
                    preview_text=_preview_text_for_range(
                        db, to_start.verse_id, to_end.verse_id
                    ),
                )
            )

        payload.append(
            CrossReferenceVerse(
                verse_id=verse.verse_id,
                book=verse.book.name,
                chapter=verse.chapter,
                verse=verse.verse,
                cross_references=items,
            )
        )

    return VerseCrossReferencesResponse(
        reference=format_ref(start, end), verses=payload
    )


def list_notes(db: Session, verse_id: int | None = None) -> list[VerseNote]:
    """list verse notes, optionally filtered by verse id."""
    stmt = (
        select(VerseNotes)
        .options(joinedload(VerseNotes.verse).joinedload(BibleVerses.book))
        .order_by(VerseNotes.updated_at.desc(), VerseNotes.note_id.desc())
    )
    if verse_id is not None:
        stmt = stmt.where(VerseNotes.verse_id == verse_id)
    rows = db.scalars(stmt).all()
    return [verse_note_schema(row) for row in rows]


def create_note(db: Session, payload: VerseNote) -> VerseNote:
    """Create a verse note for a given verse id."""
    if payload.verse_id is None:
        raise HTTPException(status_code=400, detail="verse_id is required.")

    verse_exists = db.scalar(
        select(BibleVerses.verse_id).where(BibleVerses.verse_id == payload.verse_id)
    )
    if verse_exists is None:
        raise HTTPException(status_code=400, detail="verse_id is invalid.")

    note = VerseNotes(verse_id=payload.verse_id, note_md=payload.note_md)
    db.add(note)
    db.commit()
    db.refresh(note)
    reloaded = db.scalar(
        select(VerseNotes)
        .where(VerseNotes.note_id == note.note_id)
        .options(joinedload(VerseNotes.verse).joinedload(BibleVerses.book))
    )
    assert reloaded is not None
    return verse_note_schema(reloaded)


def get_note(db: Session, note_id: int) -> VerseNote:
    """Retrieve one note by note id."""
    note = db.scalar(
        select(VerseNotes)
        .where(VerseNotes.note_id == note_id)
        .options(joinedload(VerseNotes.verse).joinedload(BibleVerses.book))
    )
    if note is None:
        raise HTTPException(status_code=404, detail="Verse note not found.")
    return verse_note_schema(note)


def update_note(db: Session, note_id: int, payload: VerseNote) -> VerseNote:
    """Fully update a note's verse target and markdown body."""
    note = db.scalar(select(VerseNotes).where(VerseNotes.note_id == note_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Verse note not found.")
    if payload.verse_id is None:
        raise HTTPException(status_code=400, detail="verse_id is required.")

    verse_exists = db.scalar(
        select(BibleVerses.verse_id).where(BibleVerses.verse_id == payload.verse_id)
    )
    if verse_exists is None:
        raise HTTPException(status_code=400, detail="verse_id is invalid.")

    note.verse_id = payload.verse_id
    note.note_md = payload.note_md
    db.commit()
    return get_note(db, note_id)


def patch_note(db: Session, note_id: int, payload: PartialVerseNote) -> VerseNote:
    """Partially update a note's verse target and/or markdown body."""
    note = db.scalar(select(VerseNotes).where(VerseNotes.note_id == note_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Verse note not found.")

    values = payload.model_dump(exclude_unset=True)
    if "verse_id" in values and payload.verse_id is not None:
        verse_exists = db.scalar(
            select(BibleVerses.verse_id).where(BibleVerses.verse_id == payload.verse_id)
        )
        if verse_exists is None:
            raise HTTPException(status_code=400, detail="verse_id is invalid.")
        note.verse_id = payload.verse_id
    if "note_md" in values:
        note.note_md = payload.note_md

    db.commit()
    return get_note(db, note_id)


def delete_note(db: Session, note_id: int) -> None:
    """Delete a verse note by id."""
    note = db.scalar(select(VerseNotes).where(VerseNotes.note_id == note_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Verse note not found.")
    db.delete(note)
    db.commit()


def get_sermons_for_reference(db: Session, ref: str) -> VerseSermonResponse:
    """Return sermons whose passages overlap a parsed verse reference range."""
    reference = (ref or "").strip()
    if not reference:
        raise HTTPException(
            status_code=400, detail="Provide a reference in the 'ref' query param."
        )

    try:
        start, end = parse_reference(db, reference)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    query_start = min(start.verse_id, end.verse_id)
    query_end = max(start.verse_id, end.verse_id)

    passages = db.scalars(
        select(SermonPassages)
        .where(
            SermonPassages.start_verse_id <= query_end,
            func.coalesce(SermonPassages.end_verse_id, SermonPassages.start_verse_id)
            >= query_start,
        )
        .options(
            joinedload(SermonPassages.sermon),
            joinedload(SermonPassages.start_verse).joinedload(BibleVerses.book),
            joinedload(SermonPassages.end_verse).joinedload(BibleVerses.book),
        )
    ).all()

    ranked: list[tuple[tuple[Any, ...], VerseSermonItem]] = []
    query_length = (query_end - query_start) + 1

    for passage in passages:
        sermon = passage.sermon
        start_id = passage.start_verse_id
        end_id = passage.end_verse_id or passage.start_verse_id
        start_id, end_id = min(start_id, end_id), max(start_id, end_id)
        length = (end_id - start_id) + 1

        if query_start == query_end:
            is_exact = start_id == query_start and end_id == query_end
            boundary_distance = abs(start_id - query_start) + abs(end_id - query_end)
            sort_key = (
                0 if is_exact else 1,
                length,
                boundary_distance,
                boundary_distance,
                -(sermon.preached_on.toordinal() if sermon.preached_on else 0),
                -sermon.sermon_id,
            )
        else:
            overlap_start = max(start_id, query_start)
            overlap_end = min(end_id, query_end)
            overlap_len = (
                overlap_end - overlap_start + 1 if overlap_end >= overlap_start else 0
            )
            if overlap_len <= 0:
                continue

            coverage_ratio = overlap_len / query_length
            length_diff = abs(length - query_length)
            start_diff = abs(start_id - query_start)
            end_diff = abs(end_id - query_end)
            coverage_group = 0
            if coverage_ratio < 1:
                coverage_group = 1 if coverage_ratio >= 0.5 else 2
            if coverage_ratio == 1 and length_diff >= query_length:
                coverage_group = max(coverage_group, 1)
            if coverage_ratio < 1 and length_diff >= query_length:
                coverage_group = max(coverage_group, 2)

            sort_key = (
                coverage_group,
                length_diff,
                start_diff,
                end_diff,
                -(sermon.preached_on.toordinal() if sermon.preached_on else 0),
                -sermon.sermon_id,
            )

        display_ref = passage.ref_text
        if not display_ref:
            end_verse = passage.end_verse or passage.start_verse
            display_ref = format_ref(passage.start_verse, end_verse)

        ranked.append(
            (
                sort_key,
                VerseSermonItem(
                    sermon_id=sermon.sermon_id,
                    title=sermon.title,
                    preached_on=sermon.preached_on,
                    speaker_name=sermon.speaker_name or "",
                    series_name=sermon.series_name or "",
                    reference=display_ref,
                    context_note=passage.context_note or "",
                    start_verse_id=start_id,
                    end_verse_id=end_id,
                ),
            )
        )

    ranked.sort(key=lambda item: item[0])
    items = [item for _, item in ranked]
    return VerseSermonResponse(reference=format_ref(start, end), sermons=items)
