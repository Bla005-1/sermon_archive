import logging
import re
from typing import Optional, Tuple, List, Dict, Sequence, Callable
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import F
from ..models import BibleBook, BibleVerse, VerseText, VerseCrossReference, VerseNote
from django.utils.html import escape
from markdown2 import Markdown


logger = logging.getLogger(__name__)

DASHES = r'[\-\u2012\u2013\u2014]'  # -, figure dash, en dash, em dash
BOOK_ALIASES = {
    'revelations': 'Revelation',
    'revelation of john': 'Revelation',
    'psalm': 'Psalms'
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


def get_verses(book: BibleBook, chapter: int, start_verse: int, end_verse: int) -> List[BibleVerse]:
    verses = list(
        BibleVerse.objects
        .select_related('book')
        .filter(book=book, chapter=chapter, verse__gte=start_verse, verse__lte=end_verse)
        .order_by('verse')
    )
    if not verses:
        raise LookupError('No verses found for the given reference.')
    return verses

def get_texts(verses: Sequence[BibleVerse], translation: Optional[str] = None):
    if not verses:
        return {} if translation else {}
    qs = VerseText.objects.filter(verse__in=verses)
    if translation:
        rows = qs.filter(translation=translation).values('verse_id', 'text')
        return {r['verse_id']: r['text'] for r in rows}
    rows = qs.values('translation', 'verse_id', 'text')
    out: Dict[str, Dict[int, str]] = {}
    for r in rows:
        out.setdefault(r['translation'], {})[r['verse_id']] = r['text']
    return out

def get_notes(verses: Sequence[BibleVerse]) -> Dict[int, List[dict]]:
    if not verses:
        return {}
    ids = [v.verse_id for v in verses]
    rows = (VerseNote.objects
            .filter(verse_id__in=ids)
            .order_by('created_at')
            .values('verse_id', 'note_id', 'note_md', 'created_at', 'updated_at'))
    out: Dict[int, List[dict]] = {}
    for r in rows:
        out.setdefault(r['verse_id'], []).append(dict(r))
    return out

def get_crossrefs_from(verses: Sequence[BibleVerse]) -> Dict[int, List[dict]]:
    if not verses:
        return {}
    ids = [v.verse_id for v in verses]
    qs = (VerseCrossReference.objects
          .select_related('from_verse', 'to_start_verse__book', 'to_end_verse__book')
          .filter(from_verse_id__in=ids)
          .order_by(
              'from_verse_id',
              F('votes').desc(nulls_last=True),
              'to_start_verse__book__order_num',
              'to_start_verse__chapter',
              'to_start_verse__verse',
              'to_end_verse__chapter',
              'to_end_verse__verse',
          ))
    out: Dict[int, List[dict]] = {i: [] for i in ids}
    for cr in qs:
        ts = cr.to_start_verse
        te = cr.to_end_verse or ts
        out[cr.from_verse.verse_id].append({
            'reference': format_ref(ts, te),
            'votes': cr.votes or 0,
            'note': cr.note or '',
            'to_start_id': ts.verse_id,
            'to_end_id': te.verse_id,
        })
    return out

def format_ref(start: BibleVerse, end: BibleVerse) -> str:
    if start.verse_id == end.verse_id:
        return f'{start.book.name} {start.chapter}:{start.verse}'
    return f'{start.book.name} {start.chapter}:{start.verse}-{end.verse}'


# ----------------------------
# Shared utilities for views/API
# ----------------------------

def determine_available_translations(verse_ids: Sequence[int], translation_map: Dict[str, Dict[int, str]]) -> List[str]:
    available: List[str] = []
    for name, verse_texts in translation_map.items():
        if all(vid in verse_texts for vid in verse_ids):
            available.append(name)
    return available


def select_default_translation(available: Sequence[str], *, preferred: Sequence[str] = ("ESV", "NIV", "KJV")) -> Optional[str]:
    for candidate in preferred:
        if candidate in available:
            return candidate
    return available[0] if available else None


def join_passage_text(verses: Sequence[BibleVerse], verse_text_lookup: Dict[int, str], *, superscript_fn: Optional[Callable[[int], str]] = None) -> Tuple[str, str]:
    sup = superscript_fn or (lambda n: f'<span class="sup">{n}</span>')
    plain_parts: List[str] = []
    display_parts: List[str] = []
    for verse in verses:
        text = (verse_text_lookup.get(verse.verse_id, '') or '').strip()
        marker = sup(verse.verse)
        if text:
            escaped_text = escape(text)
            display_parts.append(f'{marker} {escaped_text}')
            plain_parts.append(text)
        elif marker:
            display_parts.append(marker)
    plain_text = ' '.join(part for part in plain_parts if part).strip()
    display_text = ' '.join(part.strip() for part in display_parts if part).strip()
    return plain_text, display_text


def build_cross_reference_context(verses: Sequence[BibleVerse]) -> dict:
    if not verses:
        return {
            'has_any': False,
            'is_passage': False,
            'active_verse_id': None,
            'verse_options': [],
            'items_by_verse': {},
        }

    verse_ids = [verse.verse_id for verse in verses]
    crossrefs = list(
        VerseCrossReference.objects.select_related(
            'to_start_verse__book',
            'to_end_verse__book',
        )
        .filter(from_verse_id__in=verse_ids)
        .order_by(
            'from_verse_id',
            F('votes').desc(nulls_last=True),
            'to_start_verse__book__order_num',
            'to_start_verse__chapter',
            'to_start_verse__verse',
            'to_end_verse__chapter',
            'to_end_verse__verse',
        )
    )

    range_text_cache: Dict[Tuple[int, int], Dict[str, str]] = {}

    def resolve_range_text(start_id: int, end_id: int):
        key = (min(start_id, end_id), max(start_id, end_id))
        if key in range_text_cache:
            return range_text_cache[key]
        verses_in_range = list(
            BibleVerse.objects.select_related('book')
            .filter(verse_id__gte=key[0], verse_id__lte=key[1])
            .order_by('verse_id')
        )
        verse_text_lookup: Dict[int, str] = {}
        if verses_in_range:
            verse_text_qs = list(
                VerseText.objects.filter(
                    verse__in=verses_in_range, translation='ESV'
                ).order_by('verse__verse')
            )
            if not verse_text_qs:
                verse_text_qs = VerseText.objects.filter(verse__in=verses_in_range).order_by(
                    'translation', 'verse__verse'
                )
            for vt in verse_text_qs:
                verse_text_lookup.setdefault(vt.verse.verse_id, vt.plain_text)
        plain_text, display_text = join_passage_text(verses_in_range, verse_text_lookup)
        range_text_cache[key] = {
            'plain_text': plain_text,
            'display_text': display_text,
        }
        return range_text_cache[key]

    items_by_verse: Dict[int, List[dict]] = {vid: [] for vid in verse_ids}

    for crossref in crossrefs:
        to_start = crossref.to_start_verse
        to_end = crossref.to_end_verse or to_start
        text_info = resolve_range_text(to_start.verse_id, to_end.verse_id)
        items_by_verse.setdefault(crossref.from_verse.verse_id, []).append(
            {
                'reference': format_ref(to_start, to_end),
                'text': text_info['plain_text'],
                'votes': crossref.votes or 0,
                'note': crossref.note or '',
            }
        )

    verse_options = [
        {
            'id': verse.verse_id,
            'label': f'{verse.book.name} {verse.chapter}:{verse.verse}',
        }
        for verse in verses
    ]

    has_any = any(items_by_verse.get(vid) for vid in verse_ids)
    active_verse_id = verse_ids[0]
    return {
        'has_any': has_any,
        'is_passage': len(verses) > 1,
        'active_verse_id': active_verse_id,
        'verse_options': verse_options,
        'items_by_verse': items_by_verse,
        'initial_items': items_by_verse.get(active_verse_id, []),
    }


def build_passage_context(
    reference_text: str,
    *,
    forced_translation: str = '',
    preferred_translations: Sequence[str] = ("ESV", "NIV", "KJV"),
    markdown_renderer: Optional[Markdown] = None,
    superscript_fn: Optional[Callable[[int], str]] = None,
) -> Tuple[dict, str]:
    try:
        start_v, end_v = tolerant_parse_reference(reference_text)
    except ValueError as exc:
        return {}, str(exc)

    verses = list(
        BibleVerse.objects.filter(
            book=start_v.book,
            chapter=start_v.chapter,
            verse__gte=start_v.verse,
            verse__lte=end_v.verse,
        ).order_by('verse')
    )
    verse_ids = [v.verse_id for v in verses]

    verse_texts = VerseText.objects.filter(verse__in=verses).order_by('translation', 'verse__verse')
    translation_map: Dict[str, Dict[int, str]] = {}
    for vt in verse_texts:
        translation_map.setdefault(vt.translation, {})[vt.verse.verse_id] = vt.plain_text

    available_translations = determine_available_translations(verse_ids, translation_map)
    if forced_translation and forced_translation in available_translations:
        selected_translation = forced_translation
    else:
        selected_translation = select_default_translation(available_translations, preferred=preferred_translations) or ''

    translation_payload: Dict[str, str] = {}
    translation_display_payload: Dict[str, str] = {}
    for name, verse_lookup in translation_map.items():
        if name not in available_translations:
            continue
        plain_text, display_text = join_passage_text(verses, verse_lookup, superscript_fn=superscript_fn)
        # Tighten spacing after superscript for UI rendering by removing the
        # literal space that follows the superscript span; CSS will control gap.
        try:
            display_text = re.sub(r"</span>\s+", "</span>", display_text)
        except Exception:
            pass
        translation_payload[name] = plain_text
        translation_display_payload[name] = display_text
    verse_text = translation_payload.get(selected_translation, '')
    verse_display_text = translation_display_payload.get(selected_translation, '')

    note_map = {n.verse.verse_id: n for n in VerseNote.objects.filter(verse__in=verses)}
    is_range = len(verses) > 1
    notes_payload: List[dict] = []
    for verse in verses:
        note_obj = note_map.get(verse.verse_id)
        if note_obj and note_obj.note_md:
            html = ''
            if markdown_renderer:
                html = markdown_renderer.convert(note_obj.note_md)
            notes_payload.append(
                {
                    'label': f'{verse.book.name} {verse.chapter}:{verse.verse}',
                    'html': html,
                }
            )

    note_entry = note_map.get(verses[0].verse_id) if verses else None
    result = {
        'start_verse_id': verses[0].verse_id if verses else None,
        'end_verse_id': verses[-1].verse_id if verses else None,
        'available_translations': available_translations,
        'selected_translation': selected_translation or '',
        'translation_payload': translation_payload,
        'translation_display_payload': translation_display_payload,
        'verse_text': verse_text,
        'verse_display_text': verse_display_text,
        'is_read_only': is_range,
        'verse_numbers': [verse.verse for verse in verses],
        'notes': notes_payload,
        'heading': format_ref(start_v, end_v),
        'description': 'Compare translations across the passage.' if is_range else 'View translation text and notes for this verse.',
        'single_label': f'{start_v.book.name} {start_v.chapter}:{start_v.verse}',
        'note_text': note_entry.note_md if note_entry and note_entry.note_md else '',
        'note_html': (markdown_renderer.convert(note_entry.note_md) if markdown_renderer and note_entry and note_entry.note_md else ''),
        'cross_references': build_cross_reference_context(verses),
    }
    return result, ''


def build_api_verse_response(ref: str, *, translation_hint: Optional[str] = 'ESV') -> dict:
    start_v, end_v = tolerant_parse_reference(ref)
    verses = list(
        BibleVerse.objects.select_related('book')
        .filter(
            book=start_v.book,
            chapter=start_v.chapter,
            verse__gte=start_v.verse,
            verse__lte=end_v.verse,
        )
        .order_by('verse')
    )
    verse_ids = [v.verse_id for v in verses]

    # Build translation maps and decide selected translation requiring full coverage like views
    verse_texts = VerseText.objects.filter(verse__in=verses)
    tmap: Dict[str, Dict[int, str]] = {}
    for vt in verse_texts:
        tmap.setdefault(vt.translation, {})[vt.verse.verse_id] = vt.plain_text
    available = determine_available_translations(verse_ids, tmap)
    selected = translation_hint if translation_hint and translation_hint in available else select_default_translation(available)
    selected = selected or (available[0] if available else '')
    selected_lookup = tmap.get(selected, {})

    # Notes per verse
    notes_by_vid: Dict[int, List[dict]] = get_notes(verses)

    # Cross-refs per verse; augment with preview_text
    cr_by_vid = get_crossrefs_from(verses)

    def preview_text_for_range(to_start_id: int, to_end_id: int) -> str:
        a, b = (min(to_start_id, to_end_id), max(to_start_id, to_end_id))
        rng = list(BibleVerse.objects.filter(verse_id__gte=a, verse_id__lte=b).order_by('verse_id'))
        if not rng:
            return ''
        # Prefer ESV then any
        rows = list(VerseText.objects.filter(verse__in=rng, translation='ESV').order_by('verse__verse'))
        if not rows:
            rows = list(VerseText.objects.filter(verse__in=rng).order_by('translation', 'verse__verse'))
        lookup: Dict[int, str] = {}
        for vt in rows:
            lookup.setdefault(vt.verse.verse_id, vt.plain_text)
        plain, _ = join_passage_text(rng, lookup)
        return plain

    results = []
    for v in verses:
        notes_out = []
        for n in notes_by_vid.get(v.verse_id, []):
            notes_out.append({
                'note_id': n['note_id'],
                'note_md': n['note_md'],
                'created_at': n['created_at'].isoformat() if hasattr(n['created_at'], 'isoformat') else str(n['created_at']),
                'updated_at': n['updated_at'].isoformat() if hasattr(n['updated_at'], 'isoformat') else str(n['updated_at']),
            })
        cr_items = []
        for cr in cr_by_vid.get(v.verse_id, []):
            cr_items.append({
                'reference': cr['reference'],
                'to_start_id': cr['to_start_id'],
                'to_end_id': cr['to_end_id'],
                'preview_text': preview_text_for_range(cr['to_start_id'], cr['to_end_id']),
                'votes': cr['votes'],
                'note': cr['note'],
            })
        results.append({
            'verse_id': v.verse_id,
            'book': v.book.name,
            'chapter': v.chapter,
            'verse': v.verse,
            'translation': selected or '',
            'text': (selected_lookup.get(v.verse_id) or ''),
            'notes': notes_out,
            'cross_refs': cr_items,
        })

    return {
        'query': {'ref': ref, 'translation': translation_hint or ''},
        'count': len(results),
        'results': results,
    }
