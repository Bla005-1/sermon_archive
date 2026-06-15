"""Scripture reference extraction and persistence services."""

from __future__ import annotations

from dataclasses import dataclass
import re
from collections.abc import Iterable

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    BibleVerses,
    LibraryItemUnits,
    LibraryItemUnitsUnitType,
    ScriptureReferences,
    ScriptureReferencesSourceType,
    Sermons,
)
from app.services._mappers import bible_verse_schema, scripture_reference_schema
from app.services._reference import DASHES, format_ref, parse_reference
from app.services.scripture_books import all_book_aliases, canonical_book_name
from sermon_archive.schemas import (
    ScriptureExtractionRequest,
    ScriptureExtractionResponse,
    ScriptureReferenceCreate,
    ScriptureReference,
    ScriptureReferenceSourceType,
    ScriptureReferenceUpdate,
    PartialScriptureReference,
    UnresolvedScriptureReference,
)

PRIOR_CONTEXT_LIMIT = 1200


@dataclass(frozen=True)
class _ReferenceCandidate:
    reference_text: str
    matched_text: str
    start_offset: int
    end_offset: int
    context_text: str | None = None


@dataclass
class _ParseContext:
    book_name: str | None = None
    chapter_number: int | None = None


def _alias_fragment(alias: str) -> str:
    escaped = re.escape(alias.strip())
    escaped = escaped.replace(r"\.", r"\.?")
    escaped = escaped.replace(r"\ ", r"\s*")
    return f"{escaped}\\.?"


BOOK_PATTERN = "|".join(_alias_fragment(alias) for alias in all_book_aliases())
TAIL_PATTERN = rf"""
    (?:
        \s*(?:{DASHES})\s*(?:\d{{1,3}}\s*:\s*)?\d{{1,3}}
        |
        \s*[,;]\s*(?:\d{{1,3}}\s*:\s*)?\d{{1,3}}
        (?:\s*(?:{DASHES})\s*(?:\d{{1,3}}\s*:\s*)?\d{{1,3}})?
    )*
"""

EXPLICIT_VERSE_RE = re.compile(
    rf"""
    (?<![A-Za-z0-9])
    (?P<book>{BOOK_PATTERN})
    \s+
    (?P<body>
        \d{{1,3}}\s*:\s*\d{{1,3}}
        (?P<tail>{TAIL_PATTERN})
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

EXPLICIT_CHAPTER_RE = re.compile(
    rf"""
    (?<![A-Za-z0-9])
    (?P<book>{BOOK_PATTERN})
    \s+
    (?P<chapter>\d{{1,3}})
    (?!\s*:\s*\d)
    (?=\W|$)
    """,
    re.IGNORECASE | re.VERBOSE,
)

FIRST_PART_RE = re.compile(
    rf"""
    ^\s*
    (?P<chapter>\d{{1,3}})\s*:\s*(?P<verse>\d{{1,3}})
    (?:
        \s*(?:{DASHES})\s*
        (?:(?P<end_chapter>\d{{1,3}})\s*:\s*)?
        (?P<end_verse>\d{{1,3}})
    )?
    """,
    re.VERBOSE,
)

NEXT_PART_RE = re.compile(
    rf"""
    \s*(?P<sep>[,;])\s*
    (?:(?P<chapter>\d{{1,3}})\s*:\s*)?
    (?P<verse>\d{{1,3}})
    (?:
        \s*(?:{DASHES})\s*
        (?:(?P<end_chapter>\d{{1,3}})\s*:\s*)?
        (?P<end_verse>\d{{1,3}})
    )?
    """,
    re.VERBOSE,
)

BARE_REF_RE = re.compile(
    rf"""
    (?<![\w:])
    (?P<body>
        \d{{1,3}}\s*:\s*\d{{1,3}}
        (?P<tail>{TAIL_PATTERN})
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

VERSE_SHORTHAND_RE = re.compile(
    rf"""
    \bvv?\.\s*
    (?P<body>
        \d{{1,3}}
        (?:
            \s*(?:{DASHES})\s*\d{{1,3}}
            |
            \s*,\s*\d{{1,3}}(?:\s*(?:{DASHES})\s*\d{{1,3}})?
        )*
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

VERSE_PART_RE = re.compile(
    rf"""
    \s*(?P<sep>,)?\s*
    (?P<verse>\d{{1,3}})
    (?:
        \s*(?:{DASHES})\s*(?P<end_verse>\d{{1,3}})
    )?
    """,
    re.VERBOSE,
)


def _is_inside(span: tuple[int, int], occupied: Iterable[tuple[int, int]]) -> bool:
    start, end = span
    return any(
        start >= taken_start and end <= taken_end for taken_start, taken_end in occupied
    )


def _reference_text(
    book_name: str,
    chapter: int,
    verse: int | None = None,
    end_chapter: int | None = None,
    end_verse: int | None = None,
) -> str:
    if verse is None:
        return f"{book_name} {chapter}"
    if end_verse is None:
        return f"{book_name} {chapter}:{verse}"
    if end_chapter is None or end_chapter == chapter:
        return f"{book_name} {chapter}:{verse}-{end_verse}"
    return f"{book_name} {chapter}:{verse}-{end_chapter}:{end_verse}"


def _parse_body(book_name: str, body: str) -> list[str]:
    match = FIRST_PART_RE.match(body)
    if match is None:
        return []

    chapter = int(match.group("chapter"))
    current_chapter = chapter
    verse = int(match.group("verse"))
    end_chapter = (
        int(match.group("end_chapter")) if match.group("end_chapter") else chapter
    )
    end_verse = int(match.group("end_verse")) if match.group("end_verse") else None
    refs = [
        _reference_text(
            book_name,
            chapter,
            verse,
            end_chapter,
            end_verse,
        )
    ]

    pos = match.end()
    while pos < len(body):
        next_match = NEXT_PART_RE.match(body, pos)
        if next_match is None:
            break
        if next_match.group("chapter"):
            current_chapter = int(next_match.group("chapter"))
        verse = int(next_match.group("verse"))
        end_chapter = (
            int(next_match.group("end_chapter"))
            if next_match.group("end_chapter")
            else current_chapter
        )
        end_verse = (
            int(next_match.group("end_verse"))
            if next_match.group("end_verse")
            else None
        )
        refs.append(
            _reference_text(
                book_name,
                current_chapter,
                verse,
                end_chapter,
                end_verse,
            )
        )
        pos = next_match.end()

    return refs


def _parse_verse_shorthand(book_name: str, chapter_number: int, body: str) -> list[str]:
    refs: list[str] = []
    pos = 0
    while pos < len(body):
        match = VERSE_PART_RE.match(body, pos)
        if match is None:
            break
        verse = int(match.group("verse"))
        end_verse = int(match.group("end_verse")) if match.group("end_verse") else None
        refs.append(
            _reference_text(
                book_name,
                chapter_number,
                verse,
                chapter_number,
                end_verse,
            )
        )
        pos = match.end()
    return refs


def _resolve_candidate(
    db: Session,
    candidate: _ReferenceCandidate,
    source_type: ScriptureReferenceSourceType | None,
    source_id: int | None,
) -> tuple[ScriptureReference | None, UnresolvedScriptureReference | None]:
    try:
        start_v, end_v = parse_reference(db, candidate.reference_text)
    except ValueError as exc:
        return None, UnresolvedScriptureReference(
            matched_text=candidate.matched_text,
            reason=str(exc),
            context_text=candidate.context_text,
            start_offset=candidate.start_offset,
            end_offset=candidate.end_offset,
        )

    normalized = format_ref(start_v, end_v)
    end_id = end_v.verse_id if end_v.verse_id != start_v.verse_id else None
    return (
        ScriptureReference(
            source_type=source_type or ScriptureReferenceSourceType.library_item_unit,
            source_id=source_id or 0,
            start_verse_id=start_v.verse_id,
            end_verse_id=end_id,
            start_verse=bible_verse_schema(start_v),
            end_verse=bible_verse_schema(end_v) if end_id is not None else None,
            reference_text=normalized,
            matched_text=candidate.matched_text[:128],
            context_text=candidate.context_text,
            start_offset=candidate.start_offset,
            end_offset=candidate.end_offset,
        ),
        None,
    )


def extract_references_from_text(
    db: Session,
    text: str,
    *,
    context_text: str | None = None,
    source_type: ScriptureReferenceSourceType | None = None,
    source_id: int | None = None,
) -> ScriptureExtractionResponse:
    """Extract and resolve scripture references from text with optional prior context."""
    source_text = text or ""
    prefix = (context_text or "").strip()
    combined = f"{prefix}\n{source_text}" if prefix else source_text
    source_start = len(prefix) + 1 if prefix else 0

    explicit_spans = [match.span() for match in EXPLICIT_VERSE_RE.finditer(combined)]
    explicit_spans.extend(
        match.span() for match in EXPLICIT_CHAPTER_RE.finditer(combined)
    )

    events: list[tuple[int, int, str, re.Match[str]]] = []
    events.extend(
        (m.start(), m.end(), "explicit_verse", m)
        for m in EXPLICIT_VERSE_RE.finditer(combined)
    )
    events.extend(
        (m.start(), m.end(), "explicit_chapter", m)
        for m in EXPLICIT_CHAPTER_RE.finditer(combined)
        if not _is_inside(
            m.span(), [span for span in explicit_spans if span != m.span()]
        )
    )
    events.extend(
        (m.start(), m.end(), "bare", m)
        for m in BARE_REF_RE.finditer(combined)
        if not _is_inside(m.span(), explicit_spans)
    )
    events.extend(
        (m.start(), m.end(), "verse_shorthand", m)
        for m in VERSE_SHORTHAND_RE.finditer(combined)
        if not _is_inside(m.span(), explicit_spans)
    )
    events.sort(key=lambda item: (item[0], item[1]))

    context = _ParseContext()
    references: list[ScriptureReference] = []
    unresolved: list[UnresolvedScriptureReference] = []
    seen: set[tuple[int, int | None, int | None, int | None]] = set()

    for start, end, kind, match in events:
        refs: list[str] = []
        if kind in {"explicit_verse", "explicit_chapter"}:
            book_name = canonical_book_name(match.group("book") or "")
            if book_name is None:
                continue
            if kind == "explicit_chapter":
                chapter = int(match.group("chapter"))
                refs = [_reference_text(book_name, chapter)]
            else:
                refs = _parse_body(book_name, match.group("body"))
        elif kind == "bare":
            if context.book_name is None:
                continue
            refs = _parse_body(context.book_name, match.group("body"))
        else:
            if context.book_name is None or context.chapter_number is None:
                continue
            refs = _parse_verse_shorthand(
                context.book_name,
                context.chapter_number,
                match.group("body"),
            )

        for reference_text in refs:
            candidate = _ReferenceCandidate(
                reference_text=reference_text,
                matched_text=match.group(0).strip(),
                start_offset=max(0, start - source_start),
                end_offset=max(0, end - source_start),
            )
            resolved, failed = _resolve_candidate(db, candidate, source_type, source_id)
            if resolved is not None:
                start_verse = resolved.start_verse
                if start_verse is not None:
                    context.book_name = (
                        start_verse.book.book_name if start_verse.book else None
                    )
                    context.chapter_number = start_verse.chapter_number
                if end <= source_start:
                    continue
                key = (
                    resolved.start_verse_id,
                    resolved.end_verse_id,
                    resolved.start_offset,
                    resolved.end_offset,
                )
                if key not in seen:
                    seen.add(key)
                    resolved.display_order = len(references) + 1
                    references.append(resolved)
            elif failed is not None and end > source_start:
                unresolved.append(failed)

    return ScriptureExtractionResponse(references=references, unresolved=unresolved)


def preview_extraction(
    db: Session, payload: ScriptureExtractionRequest
) -> ScriptureExtractionResponse:
    """Preview scripture extraction without persistence."""
    return extract_references_from_text(
        db,
        payload.text,
        context_text=payload.context_text,
        source_type=payload.source_type,
        source_id=payload.source_id,
    )


def _source_enum(
    source_type: ScriptureReferenceSourceType,
) -> ScriptureReferencesSourceType:
    if source_type == ScriptureReferenceSourceType.sermon:
        return ScriptureReferencesSourceType.SERMON
    return ScriptureReferencesSourceType.LIBRARY_ITEM_UNIT


def _schema_source_type(
    source_type: ScriptureReferencesSourceType,
) -> ScriptureReferenceSourceType:
    if source_type == ScriptureReferencesSourceType.SERMON:
        return ScriptureReferenceSourceType.sermon
    return ScriptureReferenceSourceType.library_item_unit


def _validate_source(
    db: Session, source_type: ScriptureReferenceSourceType, source_id: int
) -> None:
    if source_type == ScriptureReferenceSourceType.sermon:
        _get_sermon_or_404(db, source_id)
        return

    unit = db.scalar(
        select(LibraryItemUnits).where(
            LibraryItemUnits.library_item_unit_id == source_id
        )
    )
    if unit is None:
        raise HTTPException(status_code=404, detail="Library item unit not found.")


def _get_verse_or_400(db: Session, verse_id: int, field_name: str) -> BibleVerses:
    verse = db.scalar(
        select(BibleVerses)
        .where(BibleVerses.verse_id == verse_id)
        .options(joinedload(BibleVerses.book))
    )
    if verse is None:
        raise HTTPException(status_code=400, detail=f"{field_name} is invalid.")
    return verse


def _resolve_reference_values(
    db: Session,
    *,
    reference_text: str | None,
    start_verse_id: int | None,
    end_verse_id: int | None,
) -> tuple[int, int | None, str]:
    cleaned_reference = reference_text.strip() if reference_text else None
    if cleaned_reference:
        try:
            start_v, end_v = parse_reference(db, cleaned_reference)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        end_id = end_v.verse_id if end_v.verse_id != start_v.verse_id else None
        return start_v.verse_id, end_id, format_ref(start_v, end_v)

    if start_verse_id is None:
        raise HTTPException(
            status_code=400,
            detail="reference_text or start_verse_id is required.",
        )

    start_v = _get_verse_or_400(db, start_verse_id, "start_verse_id")
    end_v = None
    if end_verse_id is not None:
        end_v = _get_verse_or_400(db, end_verse_id, "end_verse_id")

    range_end = end_v or start_v
    if start_v.verse_id > range_end.verse_id:
        start_v, range_end = range_end, start_v
    normalized = format_ref(start_v, range_end)
    end_id = range_end.verse_id if range_end.verse_id != start_v.verse_id else None
    return start_v.verse_id, end_id, normalized


def _next_display_order(
    db: Session, source_type: ScriptureReferenceSourceType, source_id: int
) -> int:
    return (
        db.scalar(
            select(func.max(ScriptureReferences.display_order)).where(
                ScriptureReferences.source_type == _source_enum(source_type),
                ScriptureReferences.source_id == source_id,
            )
        )
        or 0
    ) + 1


def _get_scripture_reference_row_or_404(
    db: Session, scripture_reference_id: int
) -> ScriptureReferences:
    row = db.scalar(
        select(ScriptureReferences)
        .where(
            ScriptureReferences.scripture_reference_id == scripture_reference_id
        )
        .options(
            joinedload(ScriptureReferences.start_verse).joinedload(BibleVerses.book),
            joinedload(ScriptureReferences.end_verse).joinedload(BibleVerses.book),
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Scripture reference not found.")
    return row


def _next_reference_id(db: Session) -> int:
    return (
        db.scalar(select(func.max(ScriptureReferences.scripture_reference_id))) or 0
    ) + 1


def _save_references(
    db: Session,
    *,
    source_type: ScriptureReferenceSourceType,
    source_id: int,
    references: list[ScriptureReference],
) -> list[ScriptureReference]:
    enum_value = _source_enum(source_type)
    db.execute(
        delete(ScriptureReferences).where(
            ScriptureReferences.source_type == enum_value,
            ScriptureReferences.source_id == source_id,
        )
    )
    next_id = _next_reference_id(db)
    rows: list[ScriptureReferences] = []
    for index, reference in enumerate(references, start=1):
        row = ScriptureReferences(
            scripture_reference_id=next_id,
            source_type=enum_value,
            source_id=source_id,
            start_verse_id=reference.start_verse_id,
            end_verse_id=reference.end_verse_id,
            reference_text=reference.reference_text,
            matched_text=reference.matched_text[:128],
            context_text=reference.context_text,
            start_offset=reference.start_offset,
            end_offset=reference.end_offset,
            display_order=index,
        )
        next_id += 1
        rows.append(row)
    db.add_all(rows)
    db.commit()
    return list_scripture_references(
        db, source_type=source_type, source_ids=[source_id]
    )


def list_scripture_references(
    db: Session,
    *,
    source_type: ScriptureReferenceSourceType,
    source_ids: list[int],
) -> list[ScriptureReference]:
    if not source_ids:
        return []
    rows = db.scalars(
        select(ScriptureReferences)
        .where(
            ScriptureReferences.source_type == _source_enum(source_type),
            ScriptureReferences.source_id.in_(source_ids),
        )
        .options(
            joinedload(ScriptureReferences.start_verse).joinedload(BibleVerses.book),
            joinedload(ScriptureReferences.end_verse).joinedload(BibleVerses.book),
        )
        .order_by(
            ScriptureReferences.source_id,
            ScriptureReferences.display_order,
            ScriptureReferences.scripture_reference_id,
        )
    ).all()
    return [scripture_reference_schema(row) for row in rows]


def list_scripture_references_for_source(
    db: Session,
    source_type: ScriptureReferenceSourceType,
    source_id: int,
) -> list[ScriptureReference]:
    _validate_source(db, source_type, source_id)
    return list_scripture_references(
        db,
        source_type=source_type,
        source_ids=[source_id],
    )


def get_scripture_reference(
    db: Session, scripture_reference_id: int
) -> ScriptureReference:
    return scripture_reference_schema(
        _get_scripture_reference_row_or_404(db, scripture_reference_id)
    )


def create_scripture_reference(
    db: Session, payload: ScriptureReferenceCreate
) -> ScriptureReference:
    _validate_source(db, payload.source_type, payload.source_id)
    start_id, end_id, normalized_ref = _resolve_reference_values(
        db,
        reference_text=payload.reference_text,
        start_verse_id=payload.start_verse_id,
        end_verse_id=payload.end_verse_id,
    )
    row = ScriptureReferences(
        scripture_reference_id=_next_reference_id(db),
        source_type=_source_enum(payload.source_type),
        source_id=payload.source_id,
        start_verse_id=start_id,
        end_verse_id=end_id,
        reference_text=normalized_ref,
        matched_text=(payload.matched_text or normalized_ref)[:128],
        context_text=payload.context_text,
        start_offset=payload.start_offset,
        end_offset=payload.end_offset,
        display_order=payload.display_order
        if payload.display_order is not None
        else _next_display_order(db, payload.source_type, payload.source_id),
    )
    db.add(row)
    db.commit()
    return get_scripture_reference(db, row.scripture_reference_id)


def update_scripture_reference(
    db: Session,
    scripture_reference_id: int,
    payload: ScriptureReferenceUpdate,
) -> ScriptureReference:
    row = _get_scripture_reference_row_or_404(db, scripture_reference_id)
    _validate_source(db, payload.source_type, payload.source_id)
    start_id, end_id, normalized_ref = _resolve_reference_values(
        db,
        reference_text=payload.reference_text,
        start_verse_id=payload.start_verse_id,
        end_verse_id=payload.end_verse_id,
    )

    row.source_type = _source_enum(payload.source_type)
    row.source_id = payload.source_id
    row.start_verse_id = start_id
    row.end_verse_id = end_id
    row.reference_text = normalized_ref
    row.matched_text = (payload.matched_text or normalized_ref)[:128]
    row.context_text = payload.context_text
    row.start_offset = payload.start_offset
    row.end_offset = payload.end_offset
    row.display_order = (
        payload.display_order if payload.display_order is not None else row.display_order
    )
    db.commit()
    return get_scripture_reference(db, scripture_reference_id)


def patch_scripture_reference(
    db: Session,
    scripture_reference_id: int,
    payload: PartialScriptureReference,
) -> ScriptureReference:
    row = _get_scripture_reference_row_or_404(db, scripture_reference_id)
    values = payload.model_dump(exclude_unset=True)

    source_type = values.get("source_type")
    if source_type is None:
        source_type = _schema_source_type(row.source_type)
    source_id = values.get("source_id", row.source_id)
    if "source_type" in values or "source_id" in values:
        _validate_source(db, source_type, source_id)
        row.source_type = _source_enum(source_type)
        row.source_id = source_id

    reference_keys = {"reference_text", "start_verse_id", "end_verse_id"}
    if any(key in values for key in reference_keys):
        start_id, end_id, normalized_ref = _resolve_reference_values(
            db,
            reference_text=values.get("reference_text"),
            start_verse_id=values.get("start_verse_id", row.start_verse_id),
            end_verse_id=values.get("end_verse_id", row.end_verse_id),
        )
        row.start_verse_id = start_id
        row.end_verse_id = end_id
        row.reference_text = normalized_ref
        if "matched_text" not in values:
            row.matched_text = normalized_ref[:128]

    if "matched_text" in values:
        matched = values["matched_text"]
        row.matched_text = (matched or row.reference_text)[:128]
    if "context_text" in values:
        row.context_text = values["context_text"]
    if "start_offset" in values:
        row.start_offset = values["start_offset"]
    if "end_offset" in values:
        row.end_offset = values["end_offset"]
    if "display_order" in values:
        display_order = values["display_order"]
        if display_order is not None:
            row.display_order = display_order

    db.commit()
    return get_scripture_reference(db, scripture_reference_id)


def delete_scripture_reference(db: Session, scripture_reference_id: int) -> None:
    row = _get_scripture_reference_row_or_404(db, scripture_reference_id)
    db.delete(row)
    db.commit()


def _unit_text(unit: LibraryItemUnits) -> str:
    return (unit.content_text_markdown or unit.content_text or "").strip()


def _unit_has_text(unit: LibraryItemUnits) -> bool:
    return bool(_unit_text(unit))


def _unit_type_value(unit: LibraryItemUnits) -> str:
    unit_type = unit.unit_type
    return unit_type.value if hasattr(unit_type, "value") else str(unit_type)


def _unit_is_text_source(unit: LibraryItemUnits) -> bool:
    return (
        _unit_type_value(unit) == LibraryItemUnitsUnitType.PARAGRAPH.value
        and _unit_has_text(unit)
    )


def _descendant_ids(
    unit_id: int, children_by_parent: dict[int | None, list[LibraryItemUnits]]
) -> set[int]:
    ids = {unit_id}
    for child in children_by_parent.get(unit_id, []):
        ids.update(_descendant_ids(child.library_item_unit_id, children_by_parent))
    return ids


def _ancestor_units(
    unit: LibraryItemUnits, units_by_id: dict[int, LibraryItemUnits]
) -> list[LibraryItemUnits]:
    ancestors: list[LibraryItemUnits] = []
    parent_id = unit.parent_library_item_unit_id
    while parent_id is not None and parent_id in units_by_id:
        parent = units_by_id[parent_id]
        ancestors.append(parent)
        parent_id = parent.parent_library_item_unit_id
    ancestors.reverse()
    return ancestors


def _root_id(unit: LibraryItemUnits, units_by_id: dict[int, LibraryItemUnits]) -> int:
    current = unit
    while (
        current.parent_library_item_unit_id is not None
        and current.parent_library_item_unit_id in units_by_id
    ):
        current = units_by_id[current.parent_library_item_unit_id]
    return current.library_item_unit_id


def _context_branch_id(
    unit: LibraryItemUnits, units_by_id: dict[int, LibraryItemUnits]
) -> int:
    ancestors = _ancestor_units(unit, units_by_id)
    for ancestor in reversed(ancestors):
        if _unit_type_value(ancestor) == LibraryItemUnitsUnitType.SECTION.value:
            return ancestor.library_item_unit_id
    for ancestor in reversed(ancestors):
        if _unit_type_value(ancestor) == LibraryItemUnitsUnitType.CHAPTER.value:
            return ancestor.library_item_unit_id
    return _root_id(unit, units_by_id)


def _library_context(
    unit: LibraryItemUnits,
    units_by_id: dict[int, LibraryItemUnits],
    prior_text_by_branch: dict[int, str],
) -> str | None:
    parts: list[str] = []
    for ancestor in _ancestor_units(unit, units_by_id):
        if ancestor.unit_title:
            parts.append(ancestor.unit_title)
    if unit.unit_title and not _unit_has_text(unit):
        parts.append(unit.unit_title)
    prior = prior_text_by_branch.get(_context_branch_id(unit, units_by_id))
    if prior:
        parts.append(prior[-PRIOR_CONTEXT_LIMIT:])
    context = "\n".join(part for part in parts if part.strip()).strip()
    return context or None


def _library_target_units(
    units: list[LibraryItemUnits], target: LibraryItemUnits
) -> list[LibraryItemUnits]:
    children_by_parent: dict[int | None, list[LibraryItemUnits]] = {}
    for unit in units:
        children_by_parent.setdefault(unit.parent_library_item_unit_id, []).append(unit)
    wanted_ids = _descendant_ids(target.library_item_unit_id, children_by_parent)
    return [
        unit
        for unit in sorted(
            units, key=lambda item: (item.unit_order, item.library_item_unit_id)
        )
        if unit.library_item_unit_id in wanted_ids and _unit_is_text_source(unit)
    ]


def _library_source_ids(db: Session, library_item_id: int, unit_id: int) -> list[int]:
    units = db.scalars(
        select(LibraryItemUnits)
        .where(LibraryItemUnits.library_item_id == library_item_id)
        .order_by(LibraryItemUnits.unit_order, LibraryItemUnits.library_item_unit_id)
    ).all()
    target = next(
        (unit for unit in units if unit.library_item_unit_id == unit_id), None
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Library item unit not found.")
    return [
        unit.library_item_unit_id for unit in _library_target_units(list(units), target)
    ] or [unit_id]


def list_library_unit_references(
    db: Session, library_item_id: int, library_item_unit_id: int
) -> list[ScriptureReference]:
    source_ids = _library_source_ids(db, library_item_id, library_item_unit_id)
    return list_scripture_references(
        db,
        source_type=ScriptureReferenceSourceType.library_item_unit,
        source_ids=source_ids,
    )


def extract_library_unit_references(
    db: Session, library_item_id: int, library_item_unit_id: int
) -> ScriptureExtractionResponse:
    units = db.scalars(
        select(LibraryItemUnits)
        .where(LibraryItemUnits.library_item_id == library_item_id)
        .order_by(LibraryItemUnits.unit_order, LibraryItemUnits.library_item_unit_id)
    ).all()
    target = next(
        (unit for unit in units if unit.library_item_unit_id == library_item_unit_id),
        None,
    )
    if target is None:
        raise HTTPException(status_code=404, detail="Library item unit not found.")

    units_by_id = {unit.library_item_unit_id: unit for unit in units}
    target_units = _library_target_units(list(units), target)
    target_ids = [unit.library_item_unit_id for unit in target_units] or [
        library_item_unit_id
    ]
    db.execute(
        delete(ScriptureReferences).where(
            ScriptureReferences.source_type
            == ScriptureReferencesSourceType.LIBRARY_ITEM_UNIT,
            ScriptureReferences.source_id.in_(target_ids),
        )
    )
    db.commit()

    saved: list[ScriptureReference] = []
    unresolved: list[UnresolvedScriptureReference] = []
    prior_text_by_branch: dict[int, str] = {}
    for unit in sorted(
        units, key=lambda item: (item.unit_order, item.library_item_unit_id)
    ):
        if not _unit_is_text_source(unit):
            continue
        text = _unit_text(unit)
        branch_id = _context_branch_id(unit, units_by_id)
        if unit.library_item_unit_id not in target_ids:
            prior_text_by_branch[branch_id] = text
            continue
        extracted = extract_references_from_text(
            db,
            text,
            context_text=_library_context(unit, units_by_id, prior_text_by_branch),
            source_type=ScriptureReferenceSourceType.library_item_unit,
            source_id=unit.library_item_unit_id,
        )
        saved.extend(
            _save_references(
                db,
                source_type=ScriptureReferenceSourceType.library_item_unit,
                source_id=unit.library_item_unit_id,
                references=extracted.references,
            )
        )
        unresolved.extend(extracted.unresolved)
        prior_text_by_branch[branch_id] = text

    return ScriptureExtractionResponse(references=saved, unresolved=unresolved)


def _get_sermon_or_404(db: Session, sermon_id: int) -> Sermons:
    sermon = db.scalar(select(Sermons).where(Sermons.sermon_id == sermon_id))
    if sermon is None:
        raise HTTPException(status_code=404, detail="Sermon not found.")
    return sermon


def list_sermon_references(db: Session, sermon_id: int) -> list[ScriptureReference]:
    _get_sermon_or_404(db, sermon_id)
    return list_scripture_references(
        db,
        source_type=ScriptureReferenceSourceType.sermon,
        source_ids=[sermon_id],
    )


def extract_sermon_references(
    db: Session, sermon_id: int
) -> ScriptureExtractionResponse:
    sermon = _get_sermon_or_404(db, sermon_id)
    text = (sermon.notes_markdown or "").strip()
    extracted = extract_references_from_text(
        db,
        text,
        source_type=ScriptureReferenceSourceType.sermon,
        source_id=sermon_id,
    )
    saved = _save_references(
        db,
        source_type=ScriptureReferenceSourceType.sermon,
        source_id=sermon_id,
        references=extracted.references,
    )
    return ScriptureExtractionResponse(
        references=saved, unresolved=extracted.unresolved
    )
