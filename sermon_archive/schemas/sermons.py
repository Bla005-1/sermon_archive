from __future__ import annotations

import datetime as dt

from pydantic import Field

from sermon_archive.schemas.attachments import Attachment
from sermon_archive.schemas.base import APIModel


class Sermon(APIModel):
    sermon_id: int | None = None
    preached_on: dt.date | None = None
    title: str
    speaker_name: str | None = None
    series_name: str | None = None
    location_name: str | None = None
    notes_markdown: str | None = None
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None
    attachments: list[Attachment] = Field(default_factory=list)


class PatchedSermon(APIModel):
    preached_on: dt.date | None = None
    title: str | None = None
    speaker_name: str | None = None
    series_name: str | None = None
    location_name: str | None = None
    notes_markdown: str | None = None


class SermonSuggestionsResponse(APIModel):
    speakers: list[str]
    series: list[str]
    locations: list[str]
