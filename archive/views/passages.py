import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from ..models import Sermon, SermonPassage
from ..services.passages import (
    PassageParseError,
    PassagePersistenceError,
    add_passage,
    delete_passage,
    parse_reference,
    update_passage_note,
)
from ..services.sermons import user_can_edit_sermons


logger = logging.getLogger(__name__)


def _passage_list_context(request, sermon: Sermon, **extra):
    ctx = {'sermon': sermon, 'can_edit_sermons': user_can_edit_sermons(request.user)}
    ctx.update(extra)
    return ctx


@login_required
def passage_preview(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    ref_text = request.GET.get('ref', '').strip()
    start_v = end_v = None
    error_message = ''
    if ref_text:
        try:
            start_v, end_v = parse_reference(ref_text)
        except PassageParseError as exc:
            error_message = str(exc)
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
    if not user_can_edit_sermons(request.user):
        return HttpResponseForbidden('You do not have permission to edit sermons.')
    ref_text = request.POST.get('ref_text', '').strip()
    context_note = request.POST.get('context_note', '').strip()
    try:
        add_passage(sermon, ref_text, context_note)
    except PassageParseError as exc:
        logger.warning('Failed to add passage to sermon %s: %s', sermon.pk, exc)
        return HttpResponseBadRequest('We could not understand that passage reference. Please use the format "Book Chapter:Verse".')
    except PassagePersistenceError:
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
    if not user_can_edit_sermons(request.user):
        return HttpResponseForbidden('You do not have permission to edit sermons.')
    deleted = delete_passage(sermon, ord)
    logger.debug('User %s requested passage delete (sermon=%s, ord=%s, deleted=%s)', request.user, sermon.pk, ord, deleted)
    return render(
        request,
        'archive/_partials/passage_list.html',
        _passage_list_context(request, sermon),
    )


@login_required
def passage_edit(request, pk: int, ord: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    if not user_can_edit_sermons(request.user):
        return HttpResponseForbidden('You do not have permission to edit sermons.')
    passage = get_object_or_404(SermonPassage, sermon=sermon, ord=ord)

    if request.method == 'POST':
        context_note = request.POST.get('context_note', '').strip()
        try:
            update_passage_note(passage, context_note)
        except PassagePersistenceError:
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
