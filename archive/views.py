"""View logic for the sermon archive application."""

import logging
import re
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import DatabaseError, transaction
from django.db.models import F, Max
from django.db.models.functions import Coalesce
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.html import escape
from django.urls import reverse
from django.views.decorators.http import require_POST
from markdown2 import Markdown

from .models import (
    Attachment,
    BibleBook,
    BibleVerse,
    Sermon,
    SermonPassage,
    VerseCrossReference,
    VerseNote,
    VerseText,
)
from .storage import AttachmentStorageError, save_attachment_file
from .verse_parser import BOOK_ALIASES, normalize_book, tolerant_parse_reference


logger = logging.getLogger(__name__)


SERMON_FIELDS = ['preached_on', 'title', 'speaker_name', 'series_name', 'location_name', 'notes_md']

PREFERRED_TRANSLATIONS = ('ESV', 'NIV', 'KJV')
_UNICODE_SUPERSCRIPT_PATTERN = re.compile(r'[\u00B2\u00B3\u00B9\u2070-\u209F]')
_SUPERSCRIPT_SPAN_PATTERN = re.compile(r'<span[^>]*class=["\']sup["\'][^>]*>.*?</span>', re.IGNORECASE | re.DOTALL)
_markdown_renderer = Markdown(extras=['fenced-code-blocks', 'tables'])


def _user_can_edit_sermons(user) -> bool:
    return user.is_authenticated and user.has_perm('archive.change_sermon')


def _passage_list_context(request, sermon, **extra):
    ctx = {'sermon': sermon, 'can_edit_sermons': _user_can_edit_sermons(request.user)}
    ctx.update(extra)
    return ctx


def _superscript_number(number: int) -> str:
    return f'<span class="sup">{number}</span>'


def _strip_superscripts(text: str) -> str:
    if not text:
        return ''
    without_unicode = _UNICODE_SUPERSCRIPT_PATTERN.sub('', text)
    return _SUPERSCRIPT_SPAN_PATTERN.sub('', without_unicode)


def _determine_available_translations(verse_ids, translation_map):
    available = []
    for name, verse_texts in translation_map.items():
        if all(vid in verse_texts for vid in verse_ids):
            available.append(name)
    return available


def _select_default_translation(available):
    for candidate in PREFERRED_TRANSLATIONS:
        if candidate in available:
            return candidate
    return available[0] if available else None


def _join_passage_text(verses, verse_text_lookup):
    plain_parts = []
    display_parts = []
    for verse in verses:
        text = (verse_text_lookup.get(verse.verse_id, '') or '').strip()
        marker = _superscript_number(verse.verse)
        if text:
            escaped_text = escape(text)
            display_parts.append(f'{marker} {escaped_text}')
            plain_parts.append(text)
        elif marker:
            display_parts.append(marker)
    plain_text = ' '.join(part for part in plain_parts if part).strip()
    display_text = ' '.join(part.strip() for part in display_parts if part).strip()
    return plain_text, display_text


def _render_markdown(text: str) -> str:
    return _markdown_renderer.convert(text or '')


def _format_reference(start, end):
    if start.verse_id == end.verse_id:
        return f'{start.book.name} {start.chapter}:{start.verse}'
    return f'{start.book.name} {start.chapter}:{start.verse}–{end.verse}'


def _resolve_reference_from_ids(verse_id_param: str, start_param: str, end_param: str) -> str:
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
        return _format_reference(start_verse, end_verse)

    return ''


def _build_cross_reference_context(verses):
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
        .annotate(vote_score=Coalesce('votes', 0))
        .order_by(
            'from_verse_id',
            '-vote_score',
            'to_start_verse__book__order_num',
            'to_start_verse__chapter',
            'to_start_verse__verse',
            'to_end_verse__chapter',
            'to_end_verse__verse',
        )
    )

    range_text_cache = {}

    def resolve_range_text(start_id: int, end_id: int):
        key = (min(start_id, end_id), max(start_id, end_id))
        if key in range_text_cache:
            return range_text_cache[key]
        verses_in_range = list(
            BibleVerse.objects.select_related('book')
            .filter(verse_id__gte=key[0], verse_id__lte=key[1])
            .order_by('verse_id')
        )
        verse_text_lookup = {}
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
                verse_text_lookup.setdefault(vt.verse.verse_id, vt.text)
        plain_text, display_text = _join_passage_text(verses_in_range, verse_text_lookup)
        range_text_cache[key] = {
            'plain_text': plain_text,
            'display_text': display_text,
        }
        return range_text_cache[key]

    items_by_verse = {vid: [] for vid in verse_ids}

    for crossref in crossrefs:
        to_start = crossref.to_start_verse
        to_end = crossref.to_end_verse or to_start
        text_info = resolve_range_text(to_start.verse_id, to_end.verse_id)
        items_by_verse.setdefault(crossref.from_verse.verse_id, []).append(
            {
                'reference': _format_reference(to_start, to_end),
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


def _load_passage_context(reference_text: str, forced_translation: str = ''):
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
    translation_map = {}
    for vt in verse_texts:
        translation_map.setdefault(vt.translation, {})[vt.verse.verse_id] = vt.text

    available_translations = _determine_available_translations(verse_ids, translation_map)
    selected_translation = ''
    if forced_translation and forced_translation in available_translations:
        selected_translation = forced_translation
    else:
        selected_translation = _select_default_translation(available_translations)

    translation_payload = {}
    translation_display_payload = {}
    for name, verse_lookup in translation_map.items():
        if name not in available_translations:
            continue
        plain_text, display_text = _join_passage_text(verses, verse_lookup)
        translation_payload[name] = plain_text
        translation_display_payload[name] = display_text
    verse_text = translation_payload.get(selected_translation, '')
    verse_display_text = translation_display_payload.get(selected_translation, '')

    note_map = {n.verse.verse_id: n for n in VerseNote.objects.filter(verse__in=verses)}
    is_range = len(verses) > 1
    notes_payload = []
    for verse in verses:
        note_obj = note_map.get(verse.verse_id)
        if note_obj and note_obj.note_md:
            notes_payload.append(
                {
                    'label': f'{verse.book.name} {verse.chapter}:{verse.verse}',
                    'html': _render_markdown(note_obj.note_md),
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
        'heading': _format_reference(start_v, end_v),
        'description': 'Compare translations across the passage.' if is_range else 'View translation text and notes for this verse.',
        'single_label': f'{start_v.book.name} {start_v.chapter}:{start_v.verse}',
        'note_text': note_entry.note_md if note_entry and note_entry.note_md else '',
        'note_html': _render_markdown(note_entry.note_md) if note_entry and note_entry.note_md else '',
        'cross_references': _build_cross_reference_context(verses),
    }
    return result, ''


def _serialize_related_passages(back_params, query_start, query_end, passages):
    if not query_start or not query_end or not passages:
        return []

    query_start, query_end = (min(query_start, query_end), max(query_start, query_end))
    query_length = (query_end - query_start) + 1
    is_single = query_start == query_end

    serialized = []

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


def _build_related_sermons(reference_text: str, translation: str, start_verse_id: int, end_verse_id: int):
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


def _build_sermon_from_post(data, instance=None):
    """Populate a Sermon instance (or stub) with POSTed data for redisplay."""

    sermon = instance or Sermon()
    for field in SERMON_FIELDS:
        if field == 'preached_on':
            raw_value = data.get(field)
            if raw_value:
                try:
                    parsed = Sermon._meta.get_field('preached_on').to_python(raw_value)
                    setattr(sermon, field, parsed)
                    sermon.preached_on_raw = ''
                    continue
                except ValidationError:
                    logger.debug('Invalid preached_on value provided: %s', raw_value)
                    sermon.preached_on_raw = raw_value
                    setattr(sermon, field, None)
                    continue
            sermon.preached_on_raw = raw_value or ''
            setattr(sermon, field, None)
            continue
        setattr(sermon, field, data.get(field, getattr(sermon, field, '')))
    return sermon

@login_required
def sermon_list(request):
    q = request.GET.get('q', '').strip()
    sermons = Sermon.objects.all()
    if q:
        sermons = sermons.filter(title__icontains=q)
        logger.debug('Filtering sermons with query "%s" (user=%s)', q, request.user)
    # Show newest first by preached_on date, with a stable tie-breaker on PK
    sermons = sermons.order_by('-preached_on', '-pk')
    return render(request, 'archive/sermon_list.html', {'sermons': sermons, 'q': q})

@login_required
def sermon_detail(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    logger.debug('User %s viewing sermon %s', request.user, pk)
    book_suggestions = [
        {'name': book.name, 'normalized': normalize_book(book.name)}
        for book in BibleBook.objects.order_by('order_num')
    ]
    back_to_results = ''
    back_reference = request.GET.get('from_ref', '').strip()
    if back_reference:
        params = {'ref': back_reference}
        back_translation = request.GET.get('from_translation', '').strip()
        if back_translation:
            params['translation'] = back_translation
        query = urlencode(params)
        back_to_results = f"{reverse('verse_tools')}?{query}#related-sermons"
    ctx = {
        'sermon': sermon,
        'book_suggestions': book_suggestions,
        'book_aliases': BOOK_ALIASES,
        'back_to_results_url': back_to_results,
        'can_edit_sermons': _user_can_edit_sermons(request.user),
    }
    return render(request, 'archive/sermon_detail.html', ctx)

@login_required
def sermon_create(request):
    if request.method == 'POST':
        data = request.POST
        try:
            sermon = Sermon.objects.create(
                preached_on=data.get('preached_on') or None,
                title=data.get('title', ''),
                speaker_name=data.get('speaker_name', ''),
                series_name=data.get('series_name', ''),
                location_name=data.get('location_name', ''),
                notes_md=data.get('notes_md', ''),
            )
        except (ValidationError, DatabaseError):
            logger.exception('Error creating sermon for user %s', request.user)
            messages.error(request, 'We could not save the sermon. Please fix any issues and try again.')
            return render(request, 'archive/sermon_form.html', {
                'sermon': _build_sermon_from_post(data),
                'is_edit': False,
            })
        messages.success(request, 'Sermon created successfully.')
        logger.info('User %s created sermon %s', request.user, sermon.pk)
        return redirect('sermon_detail', pk=sermon.pk)
    return render(request, 'archive/sermon_form.html', {
        'sermon': _build_sermon_from_post({}, Sermon()),
        'is_edit': False,
    })

@login_required
def sermon_edit(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    if request.method == 'POST':
        data = request.POST
        for f in SERMON_FIELDS:
            setattr(sermon, f, data.get(f, getattr(sermon, f)))
        try:
            sermon.save()
        except (ValidationError, DatabaseError):
            logger.exception('Error updating sermon %s for user %s', sermon.pk, request.user)
            messages.error(request, 'We could not update the sermon. Please correct any issues and try again.')
            return render(request, 'archive/sermon_form.html', {
                'sermon': _build_sermon_from_post(data, sermon),
                'is_edit': True,
            })
        messages.success(request, 'Sermon updated successfully.')
        logger.info('User %s updated sermon %s', request.user, sermon.pk)
        return redirect('sermon_detail', pk=sermon.pk)
    sermon.preached_on_raw = ''
    return render(request, 'archive/sermon_form.html', {'sermon': sermon, 'is_edit': True})


@login_required
def verse_tools(request):
    reference = request.GET.get('ref', '').strip()
    translation_hint = request.GET.get('translation', '').strip()
    if not reference:
        reference_from_ids = _resolve_reference_from_ids(
            request.GET.get('verse_id', ''),
            request.GET.get('start_verse_id', ''),
            request.GET.get('end_verse_id', ''),
        )
        if reference_from_ids:
            reference = reference_from_ids
    error_message = ''
    result = None

    if request.method == 'POST':
        action = request.POST.get('form_action')
        reference = request.POST.get('reference', '').strip()
        translation_hint = request.POST.get('selected_translation', '').strip()
        if action == 'save':
            result, error_message = _load_passage_context(reference, translation_hint)
            if error_message:
                messages.error(request, error_message)
            elif result['is_read_only']:
                messages.error(request, 'Passages are view-only. Please select a single verse to update notes.')
            else:
                verse = get_object_or_404(BibleVerse, pk=result['start_verse_id'])
                note_md = request.POST.get('note_md')
                note_original = request.POST.get('note_original', '')
                if note_md is not None and note_md != note_original:
                    with transaction.atomic():
                        VerseNote.objects.update_or_create(
                            verse=verse,
                            defaults={
                                'note_md': note_md,
                                'updated_at': timezone.now(),
                            },
                        )
                    messages.success(request, 'Notes saved successfully.')
                    logger.info('User %s updated notes for verse %s', request.user, verse.pk)
                    query_params = {'ref': reference}
                    selected = result.get('selected_translation') or translation_hint
                    if selected:
                        query_params['translation'] = selected
                    query = urlencode(query_params)
                    redirect_url = reverse('verse_tools')
                    if query:
                        redirect_url = f"{redirect_url}?{query}"
                    return redirect(redirect_url)
                if result is not None and note_md is not None:
                    result['note_text'] = note_md
                    result['note_html'] = _render_markdown(note_md) if note_md else ''
        else:
            result, error_message = _load_passage_context(reference, translation_hint)
            if error_message:
                messages.error(request, error_message)
    elif reference:
        result, error_message = _load_passage_context(reference, translation_hint)

    if not result and not error_message and reference:
        result, error_message = _load_passage_context(reference, translation_hint)

    if result and request.method != 'POST':
        # Ensure note preview reflects stored markdown when landing from redirect.
        result['note_html'] = _render_markdown(result['note_text']) if result['note_text'] else ''

    if result:
        result['related_sermons'] = _build_related_sermons(
            reference,
            result.get('selected_translation', ''),
            result['start_verse_id'],
            result['end_verse_id'],
        )

    book_suggestions = [
        {'name': book.name, 'normalized': normalize_book(book.name)}
        for book in BibleBook.objects.order_by('order_num')
    ]
    ctx = {
        'reference': reference,
        'result': result,
        'error_message': error_message,
        'book_suggestions': book_suggestions,
        'book_aliases': BOOK_ALIASES,
    }
    return render(request, 'archive/verse_tools.html', ctx)

@login_required
def passage_preview(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    ref_text = request.GET.get('ref', '').strip()
    start_v = end_v = None
    error_message = ''
    if ref_text:
        try:
            start_v, end_v = tolerant_parse_reference(ref_text)
        except ValueError as e:
            error_message = str(e)
            logger.warning('Passage preview parse error for sermon %s: %s', sermon.pk, error_message)
    ctx = {
        'sermon': sermon,
        'ref_text': ref_text,
        'start_v': start_v,
        'end_v': end_v,
        'error_message': error_message,
    }
    return render(request, 'archive/_partials/passage_preview.html', ctx)

@login_required
@require_POST
def passage_add(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    if not _user_can_edit_sermons(request.user):
        return HttpResponseForbidden('You do not have permission to edit sermons.')
    ref_text = request.POST.get('ref_text', '').strip()
    context_note = request.POST.get('context_note', '').strip()
    try:
        start_v, end_v = tolerant_parse_reference(ref_text)
    except ValueError as e:
        logger.warning('Failed to add passage to sermon %s: %s', sermon.pk, e)
        return HttpResponseBadRequest('We could not understand that passage reference. Please use the format "Book Chapter:Verse".')
    next_ord = (sermon.passages.aggregate(m=Max('ord'))['m'] or 0) + 1
    try:
        SermonPassage.objects.create(
            sermon=sermon, start_verse=start_v, end_verse=end_v,
            context_note=context_note, ord=next_ord, ref_text=ref_text
        )
    except DatabaseError:
        logger.exception('Database error adding passage "%s" to sermon %s', ref_text, sermon.pk)
        return HttpResponseBadRequest('We ran into a problem while saving that passage. Please try again.')
    logger.info('User %s added passage "%s" to sermon %s', request.user, ref_text, sermon.pk)
    return render(
        request,
        'archive/_partials/passage_list.html',
        _passage_list_context(request, sermon),
    )

@login_required
def passage_delete(request, pk: int, ord: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    if not _user_can_edit_sermons(request.user):
        return HttpResponseForbidden('You do not have permission to edit sermons.')
    deleted, _ = SermonPassage.objects.filter(sermon=sermon, ord=ord).delete()
    logger.debug('User %s requested passage delete (sermon=%s, ord=%s, deleted=%s)', request.user, sermon.pk, ord, deleted)
    for i, sp in enumerate(sermon.passages.order_by('ord'), start=1):
        if sp.ord != i:
            sp.ord = i
            sp.save(update_fields=['ord'])
    return render(
        request,
        'archive/_partials/passage_list.html',
        _passage_list_context(request, sermon),
    )

@login_required
def passage_edit(request, pk: int, ord: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    if not _user_can_edit_sermons(request.user):
        return HttpResponseForbidden('You do not have permission to edit sermons.')
    passage = get_object_or_404(SermonPassage, sermon=sermon, ord=ord)

    if request.method == 'POST':
        context_note = request.POST.get('context_note', '').strip()
        passage.context_note = context_note
        try:
            passage.save(update_fields=['context_note'])
        except DatabaseError:
            logger.exception('Database error updating passage %s on sermon %s', passage.pk, sermon.pk)
            return HttpResponseBadRequest('We could not save the passage note. Please try again.')
        logger.info('User %s updated passage %s note for sermon %s', request.user, passage.pk, sermon.pk)
        return render(
            request,
            'archive/_partials/passage_list.html',
            _passage_list_context(request, sermon),
        )

    if request.GET.get('cancel'):
        return render(
            request,
            'archive/_partials/passage_list.html',
            _passage_list_context(request, sermon),
        )

    return render(
        request,
        'archive/_partials/passage_list.html',
        _passage_list_context(request, sermon, editing_passage=passage),
    )


@login_required
@require_POST
def attachment_upload(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    file: UploadedFile = request.FILES.get('attachment')
    if not file:
        logger.warning('Attachment upload with no file for sermon %s', sermon.pk)
        return HttpResponseBadRequest('Please choose a file to upload.')
    try:
        rel_path, meta = save_attachment_file(sermon, file)
    except AttachmentStorageError as exc:
        logger.exception('Attachment upload failed for sermon %s', sermon.pk)
        return HttpResponseBadRequest(str(exc))
    Attachment.objects.create(
        sermon=sermon,
        rel_path=rel_path,
        original_filename=file.name,
        mime_type=meta['mime_type'],
        byte_size=meta['byte_size'],
    )
    logger.info('User %s uploaded attachment %s to sermon %s', request.user, file.name, sermon.pk)
    return render(request, 'archive/_partials/attachment_list.html', {'sermon': sermon})

@login_required
def attachment_delete(request, pk: int, att_id: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    deleted, _ = Attachment.objects.filter(sermon=sermon, id=att_id).delete()
    logger.debug('User %s deleted attachment %s from sermon %s (deleted=%s)', request.user, att_id, sermon.pk, deleted)
    return render(request, 'archive/_partials/attachment_list.html', {'sermon': sermon})

