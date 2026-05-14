import datetime as dt

from sermon_archive.schemas.base import APIModel


class Attachment(APIModel):
    attachment_id: int | None = None
    sermon_id: int | None = None
    relative_path: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
    created_at: dt.datetime | None = None


class PartialAttachment(APIModel):
    original_filename: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
