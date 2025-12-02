"""Utility functions for parsing human-entered Bible references."""

import logging
import re
from typing import Optional, Tuple

from django.core.exceptions import ObjectDoesNotExist

from apps.bible.models import BibleBook, BibleVerse


logger = logging.getLogger(__name__)

DASHES = r'[\-\u2012\u2013\u2014]'  # -, figure dash, en dash, em dash
BOOK_ALIASES = {
    # normalize roman and variants → Arabic names stored in bible_books
    'ii samuel': '2 Samuel',
    '2 sam': '2 Samuel',
    'song of songs': 'Song of Solomon',
    'canticles': 'Song of Solomon',
    # add as you encounter more…
}

class ParseError(Exception): ...

def normalize_book(raw: str) -> str:
    name = re.sub(r'\s+', ' ', raw).strip().lower()
    name = BOOK_ALIASES.get(name, name.title())
    # handle roman numerals like "II Timothy" → "2 Timothy"
    name = re.sub(r'(^| )I{1}(?= [A-Z])', r' 1', name)
    name = re.sub(r'(^| )I{2}(?= [A-Z])', r' 2', name)
    name = re.sub(r'(^| )I{3}(?= [A-Z])', r' 3', name)
    # final tidy (e.g., " 2 Timothy" → "2 Timothy")
    return re.sub(r'^\s+', '', name)

def _find_book_tolerant(name_normalized: str) -> Optional[BibleBook]:
    try:
        return BibleBook.objects.get(name__iexact=name_normalized)
    except ObjectDoesNotExist:
        logger.debug('Book lookup failed for exact name %s', name_normalized)
    # Prefix match (e.g., "john" -> "John", not "1 John")
    qs = BibleBook.objects.filter(name__istartswith=name_normalized)
    if qs.count() == 1:
        return qs.first()
    # Word-boundary contains
    try:
        wb = BibleBook.objects.filter(name__iregex=rf'(^| ){re.escape(name_normalized)}($| )')
        if wb.count() == 1:
            return wb.first()
    except Exception:  # pragma: no cover - regex errors depend on DB backend
        logger.exception('Regex search failed while looking up book %s', name_normalized)
    # Fallback: any contains, choose shortest name
    cont = list(BibleBook.objects.filter(name__icontains=name_normalized).order_by('name'))
    if len(cont) == 1:
        return cont[0]
    if cont:
        cont.sort(key=lambda b: len(b.name))
        return cont[0]
    return None

# Single regex pass: "everything until the last 'ch:verse...'" is the book
_REF_RE = re.compile(
    rf'''
    ^\s*
    (?P<book>.+?)                          # book can contain spaces and leading ordinals (e.g., "1 John")
    \s+
    (?P<ch>\d+)\s*:\s*(?P<v1>\d+)          # chapter:verse
    (?:\s*(?:{DASHES})\s*(?P<v2>\d+))?     # optional -endVerse
    \s*$
    ''',
    re.IGNORECASE | re.VERBOSE
)

def tolerant_parse_reference(ref_text: str) -> Tuple[BibleVerse, BibleVerse]:
    'Parse "Book ch:verse" or "Book ch:start-end" with unicode dashes and numeric-leading book names.'
    if not ref_text or not ref_text.strip():
        raise ValueError('Empty reference.')

    # Normalize any exotic dash to a simple hyphen to simplify matching/UX.
    cleaned = re.sub(DASHES, '-', ref_text.strip())

    m = _REF_RE.match(cleaned)
    if not m:
        # Keep the error actionable (what we accept)
        raise ValueError('References should be formatted like "Book Chapter:Verse" or "Book Chapter:Start-End".')

    book_raw = m.group('book').strip()
    ch = int(m.group('ch'))
    v1 = int(m.group('v1'))
    v2 = int(m.group('v2') or v1)

    # Let your existing normalizer + tolerant finder do their thing
    book_name = normalize_book(book_raw)
    book = _find_book_tolerant(book_name)
    if not book:
        logger.warning('Unknown Bible book provided: %s', book_raw)
        raise ValueError(f'We could not find a Bible book named "{book_raw}".')

    # Pull verses; fail clearly if either side doesn’t exist
    try:
        start_v = BibleVerse.objects.get(book=book, chapter=ch, verse=min(v1, v2))
        end_v   = BibleVerse.objects.get(book=book, chapter=ch, verse=max(v1, v2))
    except ObjectDoesNotExist:
        logger.warning('Verse lookup failed for %s %s:%s-%s', book.name, ch, v1, v2)
        raise ValueError('We could not locate that verse in the archive. Please verify the chapter and verse numbers.')

    # Safety: ensure order by primary key if ids aren’t strictly monotonic by (ch,verse)
    if start_v.verse_id > end_v.verse_id:
        start_v, end_v = end_v, start_v

    return start_v, end_v
