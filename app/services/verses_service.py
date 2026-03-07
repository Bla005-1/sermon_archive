"""Verse service implementations for passage intent, commentary, crossrefs, notes, and sermons."""

from __future__ import annotations

from typing import Any
from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    BibleVerses,
    Commentaries,
    SermonPassages,
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
    PatchedVerseNote,
    VerseCommentaryResponse,
    VerseCrossReferencesResponse,
    VerseIntentResponse,
    VerseIntentResponseTypeEnum,
    VerseNote,
    VerseSermonItem,
    VerseSermonResponse,
)
from app.services._mappers import verse_note_schema
from app.services._reference import format_ref, parse_reference


def _load_verse_range(db: Session, start: BibleVerses, end: BibleVerses) -> Sequence[BibleVerses]:
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

    return " ".join(chosen_by_verse[key].plain_text for key in sorted(chosen_by_verse.keys())).strip()


def get_passage_or_intent(
    db: Session,
    query: str,
    translation: str | None = None,
) -> VerseIntentResponse:
    """Return lightweight intent payload, normalizing references when parseable."""
    raw = (query or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="Provide a reference in the 'query' query param.")

    try:
        start, end = parse_reference(db, raw)
        normalized = format_ref(start, end)
        return VerseIntentResponse(type=VerseIntentResponseTypeEnum.TEXT, query=normalized)
    except ValueError:
        return VerseIntentResponse(type=VerseIntentResponseTypeEnum.TEXT, query=raw)


def get_commentaries(db: Session, ref: str) -> VerseCommentaryResponse:
    """Return commentary excerpts for verses resolved from a Bible reference."""
    reference = (ref or "").strip()
    if not reference:
        raise HTTPException(status_code=400, detail="Provide a reference in the 'ref' query param.")

    try:
        start, end = parse_reference(db, reference)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    verses = _load_verse_range(db, start, end)
    if not verses:
        return VerseCommentaryResponse(reference=format_ref(start, end), count=0, items=[])

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
        .order_by(Commentaries.start_verse_id, Commentaries.end_verse_id, Commentaries.commentary_id)
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
                start=CommentaryStart(book=start_v.book.name, chapter=start_v.chapter, verse=start_v.verse),
                end=CommentaryEnd(book=end_v.book.name, chapter=end_v.chapter, verse=end_v.verse),
            )
        )

    return VerseCommentaryResponse(reference=format_ref(start, end), count=len(items), items=items)


def get_cross_references(db: Session, ref: str) -> VerseCrossReferencesResponse:
    """Return verse-level outbound cross references for a resolved reference range."""
    reference = (ref or "").strip()
    if not reference:
        raise HTTPException(status_code=400, detail="Provide a reference in the 'ref' query param.")

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
        .order_by(VerseCrossrefs.from_verse_id, desc(VerseCrossrefs.votes), VerseCrossrefs.id)
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
                    preview_text=_preview_text_for_range(db, to_start.verse_id, to_end.verse_id),
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

    return VerseCrossReferencesResponse(reference=format_ref(start, end), verses=payload)


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

    verse_exists = db.scalar(select(BibleVerses.verse_id).where(BibleVerses.verse_id == payload.verse_id))
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

    verse_exists = db.scalar(select(BibleVerses.verse_id).where(BibleVerses.verse_id == payload.verse_id))
    if verse_exists is None:
        raise HTTPException(status_code=400, detail="verse_id is invalid.")

    note.verse_id = payload.verse_id
    note.note_md = payload.note_md
    db.commit()
    return get_note(db, note_id)


def patch_note(db: Session, note_id: int, payload: PatchedVerseNote) -> VerseNote:
    """Partially update a note's verse target and/or markdown body."""
    note = db.scalar(select(VerseNotes).where(VerseNotes.note_id == note_id))
    if note is None:
        raise HTTPException(status_code=404, detail="Verse note not found.")

    values = payload.model_dump(exclude_unset=True)
    if "verse_id" in values and payload.verse_id is not None:
        verse_exists = db.scalar(select(BibleVerses.verse_id).where(BibleVerses.verse_id == payload.verse_id))
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
        raise HTTPException(status_code=400, detail="Provide a reference in the 'ref' query param.")

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
            func.coalesce(SermonPassages.end_verse_id, SermonPassages.start_verse_id) >= query_start,
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
            overlap_len = overlap_end - overlap_start + 1 if overlap_end >= overlap_start else 0
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
