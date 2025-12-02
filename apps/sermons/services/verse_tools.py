from __future__ import annotations

import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from django.db.models import F
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from django.db import transaction

from markdown2 import Markdown

from ..models import (
    BibleVerse,
    BibleWidgetVerse,
    SermonPassage,
    VerseNote,
    VerseText,
)
from ..utils.reference_parser import (
    BOOK_ALIASES,
    build_passage_context,
    format_ref,
)

PREFERRED_TRANSLATIONS = ('ESV', 'NIV', 'KJV')
_markdown_renderer = Markdown(extras=['fenced-code-blocks', 'tables'])

_SUPERSCRIPT_DIGIT_RE = re.compile(r'[\u2070\u00B9\u00B2\u00B3\u2074-\u2079]')
_SUPERSCRIPT_SPAN_RE = re.compile(r'<span[^>]*class="sup"[^>]*>.*?</span>', re.IGNORECASE)


def render_markdown(text: Optional[str]) -> str:
    return _markdown_renderer.convert(text or '')


def superscript_number(number: int) -> str:
    return f'<span class="sup">{number}</span>'


def strip_superscripts(text: str) -> str:
    if not text:
        return ''
    cleaned = _SUPERSCRIPT_SPAN_RE.sub(' ', text)
    cleaned = _SUPERSCRIPT_DIGIT_RE.sub(' ', cleaned)
    return cleaned


def load_passage_context(reference_text: str, forced_translation: str = ''):
    result, error = build_passage_context(
        reference_text,
        forced_translation=forced_translation,
        preferred_translations=PREFERRED_TRANSLATIONS,
        markdown_renderer=_markdown_renderer,
        superscript_fn=superscript_number,
        include_cross_references=False,
        include_commentaries=False,
    )
    return result, error


def resolve_reference_from_ids(verse_id_param: str, start_param: str, end_param: str) -> str:
    verse_id_param = (verse_id_param or '').strip()
    start_param = (start_param or '').strip()
    end_param = (end_param or '').strip()

    if verse_id_param:
        try:
            verse_id = int(verse_id_param)
            verse = BibleVerse.objects.select_related('book').get(pk=verse_id)
            return f'{verse.book.name} {verse.chapter}:{verse.verse}'
        except (ValueError, BibleVerse.DoesNotExist):
            return ''

    if start_param:
        try:
            start_id = int(start_param)
        except ValueError:
            return ''
        try:
            start_verse = BibleVerse.objects.select_related('book').get(pk=start_id)
        except BibleVerse.DoesNotExist:
            return ''
        end_verse = start_verse
        if end_param:
            try:
                end_id = int(end_param)
                end_verse = BibleVerse.objects.select_related('book').get(pk=end_id)
            except (ValueError, BibleVerse.DoesNotExist):
                end_verse = start_verse
        if end_verse.verse_id < start_verse.verse_id:
            start_verse, end_verse = end_verse, start_verse
        return format_ref(start_verse, end_verse)

    return ''


def build_related_sermons(
    reference_text: str,
    translation: str,
    start_verse_id: int,
    end_verse_id: int,
) -> List[Mapping[str, object]]:
    if not start_verse_id or not end_verse_id:
        return []

    query_start = min(start_verse_id, end_verse_id)
    query_end = max(start_verse_id, end_verse_id)

    passages = list(
        SermonPassage.objects.select_related('sermon', 'start_verse__book', 'end_verse__book')
        .annotate(
            start_id=F('start_verse__verse_id'),
            end_id=Coalesce('end_verse__verse_id', F('start_verse__verse_id')),
        )
        .filter(start_id__lte=query_end, end_id__gte=query_start)
    )

    back_params = {}
    if reference_text:
        back_params['from_ref'] = reference_text
    if translation:
        back_params['from_translation'] = translation

    return _serialize_related_passages(back_params, query_start, query_end, passages)


def _serialize_related_passages(back_params, query_start, query_end, passages):
    if not query_start or not query_end or not passages:
        return []

    query_start, query_end = (min(query_start, query_end), max(query_start, query_end))
    query_length = (query_end - query_start) + 1
    is_single = query_start == query_end

    serialized: List = []

    for passage in passages:
        sermon = passage.sermon
        start_id = getattr(passage, 'start_id', None)
        if start_id is None:
            start_id = getattr(passage, 'start_verse_id', None) or passage.start_verse.verse_id
        end_id = getattr(passage, 'end_id', None)
        if end_id is None:
            if passage.end_verse_id:
                end_id = passage.end_verse.verse_id
            else:
                end_id = start_id

        length = (end_id - start_id) + 1

        detail_url = reverse('sermon_detail', kwargs={'pk': sermon.pk})
        if back_params:
            from urllib.parse import urlencode

            detail_url = f"{detail_url}?{urlencode(back_params)}"

        display_text = passage.ref_text or passage.ref_display()

        payload = {
            'sermon': sermon,
            'ref_text': display_text,
            'context_note': passage.context_note or '',
            'detail_url': detail_url,
        }

        if is_single:
            is_exact = start_id == query_start and end_id == query_end
            boundary_distance = abs(start_id - query_start) + abs(end_id - query_end)
            date_key = -sermon.preached_on.toordinal() if sermon.preached_on else float('inf')
            sort_key = (
                0 if is_exact else 1,
                length,
                boundary_distance,
                date_key,
                -sermon.pk,
            )
        else:
            overlap_start = max(start_id, query_start)
            overlap_end = min(end_id, query_end)
            overlap_length = overlap_end - overlap_start + 1 if overlap_end >= overlap_start else 0
            if overlap_length <= 0:
                continue
            coverage_ratio = overlap_length / query_length
            length_diff = abs(length - query_length)
            start_diff = abs(start_id - query_start)
            end_diff = abs(end_id - query_end)
            date_key = -sermon.preached_on.toordinal() if sermon.preached_on else float('inf')
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
                -overlap_length,
                date_key,
                -sermon.pk,
            )

        serialized.append((sort_key, payload))

    serialized.sort(key=lambda item: item[0])
    return [item[1] for item in serialized]


def update_note_for_verse(verse: BibleVerse, note_md: str) -> VerseNote:
    with transaction.atomic():
        note, _ = VerseNote.objects.update_or_create(
            verse=verse,
            defaults={
                'note_md': note_md,
                'updated_at': timezone.now(),
            },
        )
    return note


def build_widget_display_text(result_payload: Mapping, translation: str) -> str:
    translation_map: Mapping[str, str] = result_payload.get('translation_payload') or {}
    verse_text = (translation_map.get(translation) or '').strip()
    if not verse_text:
        return ''

    start_id = int(result_payload.get('start_verse_id') or 0)
    end_id = int(result_payload.get('end_verse_id') or 0)

    if not start_id or not end_id or end_id == start_id:
        return verse_text

    a, b = (min(start_id, end_id), max(start_id, end_id))
    verses_in_range = list(BibleVerse.objects.filter(verse_id__gte=a, verse_id__lte=b).order_by('verse_id'))
    vt_rows = list(
        VerseText.objects.filter(verse__in=verses_in_range, translation=translation).order_by('verse__verse')
    )
    if not vt_rows:
        vt_rows = list(
            VerseText.objects.filter(verse__in=verses_in_range).order_by('translation', 'verse__verse')
        )
    lookup = {}
    for row in vt_rows:
        lookup.setdefault(row.verse.verse_id, row.plain_text)

    parts: List[str] = []
    for verse in verses_in_range:
        text = (lookup.get(verse.verse_id) or '').strip()
        if not text:
            continue
        parts.append(f'[{verse.verse}]{text}')
    return ' '.join(parts).strip() or verse_text


__all__ = [
    'BOOK_ALIASES',
    'BibleWidgetVerse',
    'PREFERRED_TRANSLATIONS',
    'build_related_sermons',
    'build_widget_display_text',
    'load_passage_context',
    'render_markdown',
    'resolve_reference_from_ids',
    'strip_superscripts',
    'superscript_number',
    'update_note_for_verse',
]
