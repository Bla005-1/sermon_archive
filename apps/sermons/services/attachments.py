from __future__ import annotations

from typing import Tuple

from django.core.files.uploadedfile import UploadedFile
from django.db import DatabaseError

from .. import storage
from ..models import Attachment, Sermon


class AttachmentServiceError(Exception):
    pass


class AttachmentPersistenceError(AttachmentServiceError):
    pass


def upload_attachment(sermon: Sermon, file: UploadedFile) -> Tuple[Attachment, dict]:
    try:
        rel_path, meta = storage.save_attachment_file(sermon, file)
    except storage.AttachmentStorageError as exc:
        raise AttachmentServiceError(str(exc)) from exc

    try:
        attachment = Attachment.objects.create(
            sermon=sermon,
            rel_path=rel_path,
            original_filename=file.name,
            mime_type=meta['mime_type'],
            byte_size=meta['byte_size'],
        )
    except DatabaseError as exc:
        raise AttachmentPersistenceError('Unable to save attachment metadata.') from exc
    return attachment, meta


def delete_attachment(sermon: Sermon, attachment_id: int) -> int:
    deleted, _ = Attachment.objects.filter(sermon=sermon, pk=attachment_id).delete()
    return deleted
