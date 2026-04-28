"""Reference parsing and formatting helpers for Bible verse lookups."""

from __future__ import annotations

import re
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import BibleBooks, BibleVerses

DASHES = r"[\-\u2012\u2013\u2014]"
BOOK_ALIASES = {
    "revelations": "Revelation",
    "revelation of john": "Revelation",
    "psalm": "Psalms",
}

_REF_RE = re.compile(
    rf"""
    ^\s*
    (?P<book>.+?)
    \s+
    (?P<ch>\d+)\s*:\s*(?P<v1>\d+)
    (?:\s*(?:{DASHES})\s*(?P<v2>\d+))?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_CHAPTER_ONLY_RE = re.compile(
    r"""
    ^\s*
    (?P<book>.+?)
    \s+
    (?P<ch>\d+)
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)


def normalize_book(raw: str) -> str:
    """Normalize free-form Bible book text to a canonical lookup string."""
    name = re.sub(r"\s+", " ", raw).strip().lower()
    name = BOOK_ALIASES.get(name, name.title())
    name = re.sub(r"(^| )I{1}(?= [A-Z])", r" 1", name)
    name = re.sub(r"(^| )I{2}(?= [A-Z])", r" 2", name)
    name = re.sub(r"(^| )I{3}(?= [A-Z])", r" 3", name)
    return re.sub(r"^\s+", "", name)


def _find_book_tolerant(db: Session, name_normalized: str) -> Optional[BibleBooks]:
    """Find a Bible book with exact, prefix, word-boundary, and contains fallback matching."""
    exact = db.scalar(
        select(BibleBooks).where(
            func.lower(BibleBooks.book_name) == name_normalized.lower()
        )
    )
    if exact is not None:
        return exact

    prefix = db.scalars(
        select(BibleBooks)
        .where(BibleBooks.book_name.ilike(f"{name_normalized}%"))
        .order_by(func.length(BibleBooks.book_name), BibleBooks.book_name)
    ).all()
    if len(prefix) == 1:
        return prefix[0]

    contains = db.scalars(
        select(BibleBooks)
        .where(BibleBooks.book_name.ilike(f"%{name_normalized}%"))
        .order_by(func.length(BibleBooks.book_name), BibleBooks.book_name)
    ).all()
    if contains:
        return contains[0]
    return None


def parse_reference(
    db: Session, reference_text: str
) -> tuple[BibleVerses, BibleVerses]:
    """Parse book/chapter[/verse[-verse]] input and return canonical start/end verse rows."""
    if not reference_text or not reference_text.strip():
        raise ValueError("Empty reference.")

    cleaned = re.sub(DASHES, "-", reference_text.strip())
    match = _REF_RE.match(cleaned)
    chapter_match = None if match else _CHAPTER_ONLY_RE.match(cleaned)
    if not match and not chapter_match:
        raise ValueError(
            'References should be formatted like "Book Chapter", '
            '"Book Chapter:Verse", or "Book Chapter:Start-End".'
        )

    source = chapter_match or match
    if source is None:
        raise ValueError("We could not understand that reference.")

    book_name = normalize_book(source.group("book"))
    chapter = int(source.group("ch"))

    book = _find_book_tolerant(db, book_name)
    if book is None:
        raise ValueError(
            f'We could not find a Bible book named "{source.group("book")}".'
        )

    if chapter_match is not None:
        verses = db.scalars(
            select(BibleVerses)
            .where(
                BibleVerses.book_id == book.book_id,
                BibleVerses.chapter_number == chapter,
            )
            .order_by(BibleVerses.verse_number)
        ).all()
        if not verses:
            raise ValueError("We could not locate that chapter in the archive.")
        start_v = verses[0]
        end_v = verses[-1]
    else:
        assert match is not None
        v1 = int(match.group("v1"))
        v2 = int(match.group("v2")) if match.group("v2") else v1
        low = min(v1, v2)
        high = max(v1, v2)

        start_v = db.scalar(
            select(BibleVerses).where(
                BibleVerses.book_id == book.book_id,
                BibleVerses.chapter_number == chapter,
                BibleVerses.verse_number == low,
            )
        )
        end_v = db.scalar(
            select(BibleVerses).where(
                BibleVerses.book_id == book.book_id,
                BibleVerses.chapter_number == chapter,
                BibleVerses.verse_number == high,
            )
        )
        if start_v is None or end_v is None:
            raise ValueError("We could not locate that verse in the archive.")

    if start_v.verse_id > end_v.verse_id:
        start_v, end_v = end_v, start_v
    return start_v, end_v


def format_ref(start: BibleVerses, end: BibleVerses) -> str:
    """Render a verse range into a normalized human-readable reference."""
    if start.verse_id == end.verse_id:
        return f"{start.book.book_name} {start.chapter_number}:{start.verse_number}"
    if start.book_id == end.book_id:
        if start.chapter_number == end.chapter_number:
            return (
                f"{start.book.book_name} {start.chapter_number}:"
                f"{start.verse_number}-{end.verse_number}"
            )
        return (
            f"{start.book.book_name} {start.chapter_number}:{start.verse_number}-"
            f"{end.chapter_number}:{end.verse_number}"
        )
    return (
        f"{start.book.book_name} {start.chapter_number}:{start.verse_number} - "
        f"{end.book.book_name} {end.chapter_number}:{end.verse_number}"
    )
