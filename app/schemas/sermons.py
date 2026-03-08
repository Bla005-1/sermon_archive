from __future__ import annotations

from datetime import datetime, date

from pydantic import Field

from app.schemas.attachments import Attachment
from app.schemas.base import APIModel
from app.schemas.verses import BibleVerse


class SermonPassage(APIModel):
    id: int | None = None
    sermon: int | None = None
    start_verse: BibleVerse | None = None
    end_verse: BibleVerse | None = None
    start_verse_id: int | None = None
    end_verse_id: int | None = None
    ref_text: str | None = None
    context_note: str | None = None
    ord: int | None = None


class PartialSermonPassage(APIModel):
    start_verse_id: int | None = None
    end_verse_id: int | None = None
    ref_text: str | None = None
    context_note: str | None = None


class Sermon(APIModel):
    sermon_id: int | None = None
    preached_on: date | None = None
    title: str
    speaker_name: str | None = None
    series_name: str | None = None
    location_name: str | None = None
    notes_md: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    passages: list[SermonPassage] = Field(default_factory=list)
    attachments: list[Attachment] = Field(default_factory=list)


class PatchedSermon(APIModel):
    preached_on: date | None = None
    title: str | None = None
    speaker_name: str | None = None
    series_name: str | None = None
    location_name: str | None = None
    notes_md: str | None = None


class SermonSuggestionsResponse(APIModel):
    speakers: list[str]
    series: list[str]
    locations: list[str]
