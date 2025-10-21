import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import BibleBook, Sermon
from ..services.sermons import (
    SermonServiceError,
    build_sermon_from_post,
    create_sermon,
    update_sermon,
    user_can_edit_sermons,
)
from ..utils.reference_parser import BOOK_ALIASES, normalize_book


logger = logging.getLogger(__name__)


@login_required
def sermon_list(request):
    q = request.GET.get('q', '').strip()
    sermons = Sermon.objects.all()
    if q:
        sermons = sermons.filter(title__icontains=q)
        logger.debug('Filtering sermons with query "%s" (user=%s)', q, request.user)
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
        from urllib.parse import urlencode
        from django.urls import reverse

        query = urlencode(params)
        back_to_results = f"{reverse('verse_tools')}?{query}#related-sermons"
    ctx = {
        'sermon': sermon,
        'book_suggestions': book_suggestions,
        'book_aliases': BOOK_ALIASES,
        'back_to_results_url': back_to_results,
        'can_edit_sermons': user_can_edit_sermons(request.user),
    }
    return render(request, 'archive/sermon_detail.html', ctx)


@login_required
def sermon_create(request):
    if request.method == 'POST':
        data = request.POST
        try:
            sermon = create_sermon(data)
        except SermonServiceError:
            logger.exception('Error creating sermon for user %s', request.user)
            messages.error(request, 'We could not save the sermon. Please fix any issues and try again.')
            return render(
                request,
                'archive/sermon_form.html',
                {
                    'sermon': build_sermon_from_post(data),
                    'is_edit': False,
                },
            )
        messages.success(request, 'Sermon created successfully.')
        logger.info('User %s created sermon %s', request.user, sermon.pk)
        from django.urls import reverse

        return redirect(reverse('sermon_detail', kwargs={'pk': sermon.pk}))
    return render(
        request,
        'archive/sermon_form.html',
        {
            'sermon': build_sermon_from_post({}, Sermon()),
            'is_edit': False,
        },
    )


@login_required
def sermon_edit(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    if request.method == 'POST':
        data = request.POST
        try:
            update_sermon(sermon, data)
        except SermonServiceError:
            logger.exception('Error updating sermon %s for user %s', sermon.pk, request.user)
            messages.error(request, 'We could not update the sermon. Please correct any issues and try again.')
            return render(
                request,
                'archive/sermon_form.html',
                {
                    'sermon': build_sermon_from_post(data, sermon),
                    'is_edit': True,
                },
            )
        messages.success(request, 'Sermon updated successfully.')
        logger.info('User %s updated sermon %s', request.user, sermon.pk)
        from django.urls import reverse

        return redirect(reverse('sermon_detail', kwargs={'pk': sermon.pk}))
    sermon.preached_on_raw = ''
    return render(request, 'archive/sermon_form.html', {'sermon': sermon, 'is_edit': True})
