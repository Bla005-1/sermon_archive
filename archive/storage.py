"""Utilities for persisting uploaded sermon attachments."""

from __future__ import annotations

import logging
import mimetypes
import os
import uuid
from datetime import date

from django.conf import settings


logger = logging.getLogger(__name__)


class AttachmentStorageError(RuntimeError):
    """Raised when an attachment cannot be persisted to disk."""


def _get_base_storage() -> str:
    """Return the configured storage root, defaulting to the current directory."""
    return getattr(settings, 'SERMON_STORAGE_ROOT', '.')


def _build_storage_path(base_storage: str, sermon) -> str:
    """Create the directory path where files for the sermon should live."""

    year = sermon.preached_on.year if getattr(sermon, 'preached_on', None) else date.today().year
    root = os.path.join(base_storage, str(year), str(sermon.id))
    logger.debug('Resolved attachment storage root %s for sermon %s', root, sermon.id)
    return root


def save_attachment_file(sermon, uploaded_file):
    """Persist an uploaded file for a sermon and return its relative path and metadata.

    Any filesystem failures are logged and converted into :class:`AttachmentStorageError`
    so that callers can present a descriptive message to the client.
    """

    base_storage = _get_base_storage()
    root = _build_storage_path(base_storage, sermon)

    try:
        os.makedirs(root, exist_ok=True)
    except OSError as exc:  # pragma: no cover - exercised in filesystem errors
        logger.exception('Unable to create attachment directory %s for sermon %s', root, sermon.id)
        raise AttachmentStorageError('Unable to prepare a storage location for the attachment.') from exc

    fn = f'{uuid.uuid4().hex}__{uploaded_file.name}'
    abs_path = os.path.join(root, fn)
    logger.info('Saving attachment %s to %s for sermon %s', uploaded_file.name, abs_path, sermon.id)

    try:
        with open(abs_path, 'wb') as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
    except OSError as exc:  # pragma: no cover - exercised in filesystem errors
        logger.exception('Unable to write attachment %s for sermon %s', uploaded_file.name, sermon.id)
        raise AttachmentStorageError('Unable to save the uploaded attachment. Please try again.') from exc

    rel_path = os.path.relpath(abs_path, base_storage)
    mime_type = mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream'
    metadata = {
        'mime_type': mime_type,
        'byte_size': getattr(uploaded_file, 'size', os.path.getsize(abs_path)),
    }

    logger.debug('Attachment %s saved for sermon %s (%s)', uploaded_file.name, sermon.id, metadata)
    return rel_path, metadata

