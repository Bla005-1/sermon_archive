from datetime import datetime, date
from enum import Enum

from pydantic import Field

from app.schemas.base import APIModel


class TestamentEnum(str, Enum):
    OT = "OT"
    NT = "NT"


class BibleBook(APIModel):
    book_id: int | None = None
    name: str
    order_num: int
    testament: TestamentEnum


class BibleVerse(APIModel):
    verse_id: int | None = None
    book: BibleBook | None = None
    chapter: int
    verse: int


class CommentaryStart(APIModel):
    book: str
    chapter: int
    verse: int


class CommentaryEnd(APIModel):
    book: str
    chapter: int
    verse: int


class CommentaryItem(APIModel):
    commentary_id: int
    father_id: int | None = None
    father_name: str
    display_name: str
    append_to_author_name: str
    text: str
    book_id: int
    start_verse_id: int
    end_verse_id: int
    reference: str
    source_url: str
    source_title: str
    default_year: int | None = None
    wiki_url: str
    start: CommentaryStart
    end: CommentaryEnd


class CrossReferenceItem(APIModel):
    reference: str
    votes: int
    note: str
    to_start_id: int
    to_end_id: int
    preview_text: str


class CrossReferenceVerse(APIModel):
    verse_id: int
    book: str
    chapter: int
    verse: int
    cross_references: list[CrossReferenceItem]


class VerseCommentaryResponse(APIModel):
    reference: str
    count: int
    items: list[CommentaryItem]


class VerseCrossReferencesResponse(APIModel):
    reference: str
    verses: list[CrossReferenceVerse]


class SearchIntentEnum(str, Enum):
    REFERENCE = "reference"
    TEXT = "text"


class VerseSearchResult(APIModel):
    order_num: int
    verse_id: int
    reference: str
    book: str
    chapter: int
    verse: int
    translation: str
    text: str


class VerseQueryResponse(APIModel):
    intent: SearchIntentEnum
    query: str
    reference: str | None = None
    verses: list[VerseSearchResult] = Field(default_factory=list)


class VerseTextSearchResponse(APIModel):
    query: str
    page: int
    total: int
    results: list[VerseSearchResult]


class VerseNote(APIModel):
    note_id: int | None = None
    verse: BibleVerse | None = None
    verse_id: int | None = None
    note_md: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PartialVerseNote(APIModel):
    verse_id: int | None = None
    note_md: str | None = None


class VerseSermonItem(APIModel):
    sermon_id: int
    title: str
    preached_on: date | None = None
    speaker_name: str
    series_name: str
    reference: str
    context_note: str
    start_verse_id: int
    end_verse_id: int


class VerseSermonResponse(APIModel):
    reference: str
    sermons: list[VerseSermonItem]
