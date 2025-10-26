import logging
import os

from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from ..models import Sermon
from ..services.attachments import (
    AttachmentPersistenceError,
    AttachmentServiceError,
    delete_attachment,
    upload_attachment,
)
from ..storage import AttachmentStorageError, resolve_attachment_path


logger = logging.getLogger(__name__)


@login_required
@require_POST
def attachment_upload(request, pk: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    file = request.FILES.get('attachment')
    if not file:
        logger.warning('Attachment upload with no file for sermon %s', sermon.pk)
        return HttpResponseBadRequest('Please choose a file to upload.')
    try:
        upload_attachment(sermon, file)
    except AttachmentPersistenceError:
        logger.exception('Attachment upload failed for sermon %s', sermon.pk)
        return HttpResponseBadRequest('We could not save that attachment metadata. Please try again.')
    except AttachmentServiceError as exc:
        logger.exception('Attachment upload failed for sermon %s', sermon.pk)
        return HttpResponseBadRequest(str(exc))
    logger.info('User %s uploaded attachment %s to sermon %s', request.user, file.name, sermon.pk)
    return render(request, 'archive/_partials/attachment_list.html', {'sermon': sermon})


@login_required
def attachment_delete(request, pk: int, att_id: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    deleted = delete_attachment(sermon, att_id)
    logger.debug('User %s deleted attachment %s from sermon %s (deleted=%s)', request.user, att_id, sermon.pk, deleted)
    return render(request, 'archive/_partials/attachment_list.html', {'sermon': sermon})


@login_required
def attachment_download(request, pk: int, att_id: int):
    sermon = get_object_or_404(Sermon, pk=pk)
    attachment = get_object_or_404(sermon.attachments, pk=att_id)

    try:
        abs_path = resolve_attachment_path(attachment.rel_path)
    except AttachmentStorageError:
        logger.exception(
            'Attachment %s for sermon %s resolved outside storage root',
            att_id,
            sermon.pk,
        )
        raise Http404('Attachment not found.')

    if not os.path.exists(abs_path):
        logger.warning(
            'Attachment %s for sermon %s missing from filesystem path %s',
            att_id,
            sermon.pk,
            abs_path,
        )
        raise Http404('Attachment not found.')

    filename = attachment.original_filename or os.path.basename(abs_path)
    response = FileResponse(open(abs_path, 'rb'), as_attachment=True, filename=filename)
    if attachment.mime_type:
        response['Content-Type'] = attachment.mime_type
    return response
