import logging
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from ..models import BibleBook, BibleVerse, BibleWidgetVerse
from ..services.bible_widget import (
    BibleWidgetPersistenceError,
    adjust_weight,
    delete_entry,
    ensure_entry,
    update_display_text,
)
from ..services.verse_tools import (
    BOOK_ALIASES,
    build_related_sermons,
    build_widget_display_text,
    load_passage_context,
    render_markdown,
    resolve_reference_from_ids,
    strip_superscripts,
    update_note_for_verse,
)
from ..utils.reference_parser import normalize_book

BIBLE_WIDGET_WARNING_LENGTH = 155

logger = logging.getLogger(__name__)


@login_required
def verse_tools(request):
    reference = request.GET.get('ref', '').strip()
    translation_hint = request.GET.get('translation', '').strip()
    if not reference:
        reference_from_ids = resolve_reference_from_ids(
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
            result, error_message = load_passage_context(reference, translation_hint)
            if error_message:
                messages.error(request, error_message)
            elif result['is_read_only']:
                messages.error(request, 'Passages are view-only. Please select a single verse to update notes.')
            else:
                verse = get_object_or_404(BibleVerse, pk=result['start_verse_id'])
                note_md = request.POST.get('note_md')
                note_original = request.POST.get('note_original', '')
                if note_md is not None and note_md != note_original:
                    update_note_for_verse(verse, note_md)
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
                    result['note_html'] = render_markdown(note_md) if note_md else ''
        elif action == 'add_to_widget':
            result, error_message = load_passage_context(reference, translation_hint)
            if error_message:
                messages.error(request, error_message)
            else:
                selected = (result.get('selected_translation') or translation_hint or '').strip()
                if not selected:
                    messages.error(request, 'Select a translation before adding to the BibleWidget.')
                else:
                    display_text = build_widget_display_text(result, selected)
                    if not display_text:
                        messages.error(request, 'No verse text is available for the selected translation.')
                    else:
                        start_id = int(result.get('start_verse_id') or 0)
                        verse = get_object_or_404(BibleVerse, pk=start_id) if start_id else None
                        try:
                            entry, created = ensure_entry(
                                verse,
                                selected,
                                result.get('heading') or reference,
                                display_text,
                            )
                        except BibleWidgetPersistenceError:
                            logger.exception('Failed to save BibleWidget verse %s', getattr(verse, 'pk', 'unknown'))
                            messages.error(request, 'We could not save that verse to the BibleWidget. Please try again.')
                        else:
                            action_word = 'Added' if created else 'Updated'
                            message_text = 'Added verse to the BibleWidget.' if created else 'Updated verse in the BibleWidget.'
                            messages.success(request, message_text)
                            logger.info(
                                'User %s %s BibleWidget verse %s (translation=%s)',
                                request.user,
                                action_word.lower(),
                                getattr(verse, 'pk', 'unknown'),
                                selected,
                            )
                            plain_length = len(strip_superscripts(display_text))
                            if plain_length > BIBLE_WIDGET_WARNING_LENGTH:
                                messages.warning(
                                    request,
                                    'This verse is %s characters long. The BibleWidget works best with about %s characters or fewer.'
                                    % (plain_length, BIBLE_WIDGET_WARNING_LENGTH),
                                )
        else:
            result, error_message = load_passage_context(reference, translation_hint)
            if error_message:
                messages.error(request, error_message)
    elif reference:
        result, error_message = load_passage_context(reference, translation_hint)

    if not result and not error_message and reference:
        result, error_message = load_passage_context(reference, translation_hint)

    if result and request.method != 'POST':
        result['note_html'] = render_markdown(result['note_text']) if result['note_text'] else ''

    if result:
        result['related_sermons'] = build_related_sermons(
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
def bible_widget_list(request):
    if request.method == 'POST':
        action = (request.POST.get('action') or '').strip()
        entry_id = (request.POST.get('entry_id') or '').strip()
        if not entry_id:
            messages.error(request, 'We could not determine which verse to update.')
            return redirect('bible_widget_list')

        entry = get_object_or_404(BibleWidgetVerse, pk=entry_id)

        if action == 'update_text':
            new_text = (request.POST.get('display_text') or '').strip()
            if not new_text:
                messages.error(request, 'Display text cannot be empty.')
                return redirect('bible_widget_list')
            try:
                update_display_text(entry, new_text)
            except BibleWidgetPersistenceError:
                logger.exception('Failed to update BibleWidget text for verse %s', entry.verse.verse_id)
                messages.error(request, 'We could not update the display text. Please try again.')
            else:
                messages.success(request, f'Updated display text for {entry.ref}.')
                logger.info('User %s updated BibleWidget display text for verse %s', request.user, entry.verse.verse_id)
            return redirect('bible_widget_list')

        if action == 'weight_up':
            old_weight = entry.weight
            try:
                updated = adjust_weight(entry, 1)
            except BibleWidgetPersistenceError:
                logger.exception('Failed to increase BibleWidget weight for verse %s', entry.verse.verse_id)
                messages.error(request, 'We could not update the weight. Please try again.')
            else:
                if updated.weight == old_weight:
                    messages.info(request, f'Weight is already at the maximum value of {old_weight}.')
                else:
                    messages.success(request, f'Increased weight to {updated.weight} for {entry.ref}.')
                    logger.info('User %s increased BibleWidget weight for verse %s to %s', request.user, entry.verse.verse_id, updated.weight)
            return redirect('bible_widget_list')

        if action == 'weight_down':
            if entry.weight <= 1:
                messages.info(request, 'Weight is already at the minimum value of 1.')
                return redirect('bible_widget_list')
            old_weight = entry.weight
            try:
                updated = adjust_weight(entry, -1)
            except BibleWidgetPersistenceError:
                logger.exception('Failed to decrease BibleWidget weight for verse %s', entry.verse.verse_id)
                messages.error(request, 'We could not update the weight. Please try again.')
            else:
                if updated.weight == old_weight:
                    messages.info(request, 'Weight is already at the minimum value of 1.')
                else:
                    messages.success(request, f'Decreased weight to {updated.weight} for {entry.ref}.')
                    logger.info('User %s decreased BibleWidget weight for verse %s to %s', request.user, entry.verse.verse_id, updated.weight)
            return redirect('bible_widget_list')

        if action == 'delete':
            try:
                delete_entry(entry)
            except BibleWidgetPersistenceError:
                logger.exception('Failed to delete BibleWidget verse %s', entry.verse.verse_id)
                messages.error(request, 'We could not remove that verse. Please try again.')
            else:
                messages.success(request, f'Removed {entry.ref} from the BibleWidget pool.')
                logger.info('User %s deleted BibleWidget verse %s', request.user, entry.verse.verse_id)
            return redirect('bible_widget_list')

        messages.error(request, 'Unsupported action for the BibleWidget verse list.')
        return redirect('bible_widget_list')

    entries = (
        BibleWidgetVerse.objects.select_related('verse__book')
        .order_by('-weight', '-updated_at')
    )
    return render(request, 'archive/bible_widget_list.html', {'entries': entries})
