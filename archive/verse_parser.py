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

