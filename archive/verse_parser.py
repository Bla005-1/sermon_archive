from typing import Tuple
from django.core.exceptions import ObjectDoesNotExist
from .models import BibleBook, BibleVerse

ALIASES = {
    'gen': 'Genesis', 'ge': 'Genesis', 'gn': 'Genesis',
    'john': 'John', 'jn': 'John',
    '1 sam': '1 Samuel', '1 samuel': '1 Samuel', 'i samuel': '1 Samuel', '1sam': '1 Samuel',
    '2 sam': '2 Samuel', '2 samuel': '2 Samuel', 'ii samuel': '2 Samuel', '2sam': '2 Samuel',
}

def normalize_book(raw: str) -> str:
    s = ' '.join(raw.lower().split())
    if s in ALIASES:
        return ALIASES[s]
    parts = s.split(' ', 1)
    if parts and parts[0] in {'1','2','3'} and len(parts) > 1:
        return f"{parts[0]} {parts[1].capitalize()}"
    return s.capitalize()

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

    if start_v.id > end_v.id:
        start_v, end_v = end_v, start_v
    return start_v, end_v

