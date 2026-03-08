"""Attachment service implementations for CRUD and upload persistence."""

from __future__ import annotations

import mimetypes
import os
import shutil
import uuid
from datetime import date
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Attachments, Sermons
from app.schemas.attachments import Attachment, PartialAttachment
from app.services._mappers import attachment_schema


def _storage_root() -> str:
    """Resolve and create the base storage root used for uploaded attachments."""
    root = os.path.abspath(os.getenv("SERMON_STORAGE_ROOT", "."))
    os.makedirs(root, exist_ok=True)
    return root


def _safe_rel_to_abs(rel_path: str) -> str:
    """Resolve an attachment relative path inside the configured storage root."""
    root = _storage_root()
    abs_path = os.path.abspath(os.path.join(root, rel_path))
    if os.path.commonpath([root, abs_path]) != root:
        raise HTTPException(
            status_code=400, detail="Attachment path is outside storage root."
        )
    return abs_path


def _get_attachment_or_404(db: Session, attachment_id: int) -> Attachments:
    """Load one attachment row or raise a 404 error."""
    attachment = db.scalar(
        select(Attachments).where(Attachments.attachment_id == attachment_id)
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return attachment


def _get_sermon_or_404(db: Session, sermon_id: int) -> Sermons:
    """Load one sermon row or raise a 404 error."""
    sermon = db.scalar(select(Sermons).where(Sermons.sermon_id == sermon_id))
    if sermon is None:
        raise HTTPException(status_code=404, detail="Sermon not found.")
    return sermon


def _get_sermon_attachment_or_404(
    db: Session, sermon_id: int, attachment_id: int
) -> Attachments:
    """Load one attachment scoped to a sermon or raise a 404 error."""
    _get_sermon_or_404(db, sermon_id)
    attachment = db.scalar(
        select(Attachments).where(
            Attachments.attachment_id == attachment_id,
            Attachments.sermon_id == sermon_id,
        )
    )
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found.")
    return attachment


def get_attachment(db: Session, attachment_id: int) -> Attachment:
    """Fetch an attachment by id."""
    return attachment_schema(_get_attachment_or_404(db, attachment_id))


def update_attachment(
    db: Session, attachment_id: int, payload: Attachment
) -> Attachment:
    """Fully update writable attachment metadata fields."""
    attachment = _get_attachment_or_404(db, attachment_id)
    attachment.original_filename = payload.original_filename
    attachment.mime_type = payload.mime_type
    attachment.byte_size = payload.byte_size
    db.commit()
    db.refresh(attachment)
    return attachment_schema(attachment)


def patch_attachment(
    db: Session, attachment_id: int, payload: PartialAttachment
) -> Attachment:
    """Partially update writable attachment metadata fields."""
    attachment = _get_attachment_or_404(db, attachment_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(attachment, key, value)
    db.commit()
    db.refresh(attachment)
    return attachment_schema(attachment)


def delete_attachment(db: Session, attachment_id: int) -> None:
    """Delete an attachment row and its stored file when present."""
    attachment = _get_attachment_or_404(db, attachment_id)
    if attachment.rel_path:
        abs_path = _safe_rel_to_abs(attachment.rel_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)
    db.delete(attachment)
    db.commit()


def list_sermon_attachments(db: Session, sermon_id: int) -> list[Attachment]:
    """List attachments for a sermon ordered by newest upload first."""
    _get_sermon_or_404(db, sermon_id)
    rows = db.scalars(
        select(Attachments)
        .where(Attachments.sermon_id == sermon_id)
        .order_by(Attachments.created_at.desc(), Attachments.attachment_id.desc())
    ).all()
    return [attachment_schema(row) for row in rows]


def create_sermon_attachment(
    db: Session,
    sermon_id: int,
    file: UploadFile | None,
    payload: Attachment | None = None,
) -> Attachment:
    """Persist an uploaded file for a sermon and create its metadata row."""
    sermon = _get_sermon_or_404(db, sermon_id)
    if file is None or not file.filename:
        raise HTTPException(status_code=400, detail="Please include a file upload.")

    root = _storage_root()
    year = sermon.preached_on.year if sermon.preached_on else date.today().year
    target_dir = os.path.join(root, str(year), str(sermon_id))
    os.makedirs(target_dir, exist_ok=True)

    stored_name = f"{uuid.uuid4().hex}__{os.path.basename(file.filename)}"
    abs_path = os.path.join(target_dir, stored_name)
    with open(abs_path, "wb") as handle:
        shutil.copyfileobj(file.file, handle)

    rel_path = os.path.relpath(abs_path, root)
    mime_type = (
        file.content_type
        or mimetypes.guess_type(file.filename)[0]
        or "application/octet-stream"
    )
    byte_size = os.path.getsize(abs_path)

    attachment = Attachments(
        sermon_id=sermon_id,
        rel_path=rel_path,
        original_filename=file.filename,
        mime_type=mime_type,
        byte_size=byte_size,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return attachment_schema(attachment)


def get_sermon_attachment_download(
    db: Session, sermon_id: int, attachment_id: int
) -> tuple[str, str, str]:
    """Resolve a sermon attachment to an existing file and return download metadata."""
    attachment = _get_sermon_attachment_or_404(
        db=db, sermon_id=sermon_id, attachment_id=attachment_id
    )
    if not attachment.rel_path:
        raise HTTPException(status_code=404, detail="Attachment file not found.")

    abs_path = _safe_rel_to_abs(attachment.rel_path)
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail="Attachment file not found.")

    filename = attachment.original_filename or Path(abs_path).name
    mime_type = attachment.mime_type or "application/octet-stream"
    return abs_path, filename, mime_type
