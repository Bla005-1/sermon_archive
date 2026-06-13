from __future__ import annotations

import datetime as dt
from enum import Enum

from pydantic import Field

from sermon_archive.schemas.base import APIModel


class LibraryContentTypeEnum(str, Enum):
    book = "book"
    devotional = "devotional"
    article = "article"
    poetic = "poetic"
    reference = "reference"
    notes = "notes"
    other = "other"


class LibraryUnitTypeEnum(str, Enum):
    page = "page"
    paragraph = "paragraph"
    section = "section"
    chapter = "chapter"
    summary = "summary"
    unknown = "unknown"


class LibraryItemFile(APIModel):
    library_item_file_id: int | None = None
    library_item_id: int | None = None
    relative_path: str | None = None
    original_filename: str | None = None
    mime_type: str | None = None
    byte_size: int | None = None
    created_at: dt.datetime | None = None


class LibraryItemUnit(APIModel):
    library_item_unit_id: int | None = None
    library_item_id: int | None = None
    parent_library_item_unit_id: int | None = None
    unit_order: int | None = None
    unit_type: LibraryUnitTypeEnum | None = None
    unit_title: str | None = None
    content_text: str | None = None
    content_text_markdown: str | None = None
    source_start_page_number: int | None = None
    source_end_page_number: int | None = None
    created_at: dt.datetime | None = None
    children: list["LibraryItemUnit"] = Field(default_factory=list)


class LibraryItem(APIModel):
    library_item_id: int | None = None
    title: str
    content_type: LibraryContentTypeEnum
    author_name: str | None = None
    description_text: str | None = None
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None
    files: list[LibraryItemFile] = Field(default_factory=list)

