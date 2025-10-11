import re
from typing import Tuple
from django.core.exceptions import ObjectDoesNotExist
from .models import BibleBook, BibleVerse

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

def parse_reference(ref_text: str) -> Tuple[BibleVerse, BibleVerse]:
    if not ref_text:
        raise ValueError('Empty reference.')
    try:
        book_part, cv = ref_text.strip().split(' ', 1)
    except ValueError:
        parts = ref_text.strip().rsplit(' ', 1)
        if len(parts) != 2:
            raise ValueError('Reference must include book and chapter:verse.')
        book_part, cv = parts[0], parts[1]

    book_name = normalize_book(book_part)
    try:
        book = BibleBook.objects.get(name__iexact=book_name)
    except ObjectDoesNotExist:
        raise ValueError(f'Unknown book: {book_part}')

    if '-' in cv:
        left, right = cv.split('-', 1)
    else:
        left, right = cv, cv

    def split_cv(x: str):
        if ':' not in x:
            raise ValueError('Missing verse number.')
        ch, vs = x.split(':', 1)
        return int(ch), int(vs)

    ch1, v1 = split_cv(left)
    ch2, v2 = split_cv(right)

    try:
        start_v = BibleVerse.objects.get(book=book, chapter=ch1, verse=v1)
        end_v = BibleVerse.objects.get(book=book, chapter=ch2, verse=v2)
    except ObjectDoesNotExist:
        raise ValueError('Verse not found in database.')

    if start_v.verse_id > end_v.verse_id:
        start_v, end_v = end_v, start_v
    return start_v, end_v


# --- Tolerant parsing helpers (do not change existing callers) ---
from typing import Optional  # local import to avoid breaking imports above

def _find_book_tolerant(name_normalized: str) -> Optional[BibleBook]:
    try:
        return BibleBook.objects.get(name__iexact=name_normalized)
    except ObjectDoesNotExist:
        pass
    # Prefix match (e.g., "john" -> "John", not "1 John")
    qs = BibleBook.objects.filter(name__istartswith=name_normalized)
    if qs.count() == 1:
        return qs.first()
    # Word-boundary contains
    try:
        wb = BibleBook.objects.filter(name__iregex=rf'(^| ){re.escape(name_normalized)}($| )')
        if wb.count() == 1:
            return wb.first()
    except Exception:
        pass
    # Fallback: any contains, choose shortest name
    cont = list(BibleBook.objects.filter(name__icontains=name_normalized).order_by('name'))
    if len(cont) == 1:
        return cont[0]
    if cont:
        cont.sort(key=lambda b: len(b.name))
        return cont[0]
    return None


def tolerant_parse_reference(ref_text: str) -> Tuple[BibleVerse, BibleVerse]:
    """A more forgiving parser that accepts common variants and unicode dashes."""
    if not ref_text:
        raise ValueError('Empty reference.')
    try:
        book_part, cv = ref_text.strip().split(' ', 1)
    except ValueError:
        parts = ref_text.strip().rsplit(' ', 1)
        if len(parts) != 2:
            raise ValueError('Reference must include book and chapter:verse.')
        book_part, cv = parts[0], parts[1]

    book_name = normalize_book(book_part)
    book = _find_book_tolerant(book_name)
    if not book:
        raise ValueError(f'Unknown book: {book_part}')

    # Support hyphen or unicode dash ranges
    if '-' in cv or re.search(DASHES, cv):
        left, right = re.split(DASHES, cv, maxsplit=1)
    else:
        left, right = cv, cv

    def split_cv(x: str):
        if ':' not in x:
            raise ValueError('Missing verse number.')
        ch, vs = x.split(':', 1)
        return int(ch), int(vs)

    ch1, v1 = split_cv(left)
    ch2, v2 = split_cv(right)

    try:
        start_v = BibleVerse.objects.get(book=book, chapter=ch1, verse=v1)
        end_v = BibleVerse.objects.get(book=book, chapter=ch2, verse=v2)
    except ObjectDoesNotExist:
        raise ValueError('Verse not found in database.')

    if start_v.verse_id > end_v.verse_id:
        start_v, end_v = end_v, start_v
    return start_v, end_v
