"""View logic for the sermon archive application."""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import DatabaseError
from django.db.models import Max
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Attachment, BibleBook, Sermon, SermonPassage
from .storage import AttachmentStorageError, save_attachment_file
from .verse_parser import BOOK_ALIASES, normalize_book, tolerant_parse_reference


logger = logging.getLogger(__name__)


SERMON_FIELDS = ['preached_on', 'title', 'speaker_name', 'series_name', 'location_name', 'notes_md']


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
    ctx = {
        'sermon': sermon,
        'book_suggestions': book_suggestions,
        'book_aliases': BOOK_ALIASES,
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
            context_note=context_note, ord=next_ord
        )
    except DatabaseError:
        logger.exception('Database error adding passage "%s" to sermon %s', ref_text, sermon.pk)
        return HttpResponseBadRequest('We ran into a problem while saving that passage. Please try again.')
    logger.info('User %s added passage "%s" to sermon %s', request.user, ref_text, sermon.pk)
    return render(request, 'archive/_partials/passage_list.html', {'sermon': sermon})

@login_required
def passage_delete(request, pk: int, ord: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    deleted, _ = SermonPassage.objects.filter(sermon=sermon, ord=ord).delete()
    logger.debug('User %s requested passage delete (sermon=%s, ord=%s, deleted=%s)', request.user, sermon.pk, ord, deleted)
    for i, sp in enumerate(sermon.passages.order_by('ord'), start=1):
        if sp.ord != i:
            sp.ord = i
            sp.save(update_fields=['ord'])
    return render(request, 'archive/_partials/passage_list.html', {'sermon': sermon})

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

