from datetime import datetime

from app.schemas.base import APIModel
from app.schemas.verses import BibleVerse


class BibleWidget(APIModel):
    id: int | None = None
    start_verse: BibleVerse | None = None
    end_verse: BibleVerse | None = None
    start_verse_id: int | None = None
    end_verse_id: int | None = None
    translation: str
    ref: str
    display_text: str
    weight: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PatchedBibleWidget(APIModel):
    start_verse_id: int | None = None
    end_verse_id: int | None = None
    translation: str | None = None
    ref: str | None = None
    display_text: str | None = None
    weight: int | None = None
