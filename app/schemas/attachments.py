from datetime import datetime

from app.schemas.base import APIModel


class Attachment(APIModel):
    attachment_id: int | None = None
    sermon: int | None = None
    rel_path: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
    created_at: datetime | None = None


class PatchedAttachment(APIModel):
    original_filename: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
