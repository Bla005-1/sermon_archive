from datetime import datetime, date
from enum import Enum

from pydantic import Field

from app.schemas.base import APIModel


class TestamentEnum(str, Enum):
    OT = "OT"
    NT = "NT"


class BibleBook(APIModel):
    book_id: int | None = None
    book_name: str
    book_order: int
    testament: TestamentEnum


class BibleVerse(APIModel):
    verse_id: int | None = None
    book: BibleBook | None = None
    chapter_number: int
    verse_number: int


class CommentaryStart(APIModel):
    book: str
    chapter_number: int
    verse_number: int


class CommentaryEnd(APIModel):
    book: str
    chapter_number: int
    verse_number: int


class CommentaryItem(APIModel):
    commentary_id: int
    father_id: int | None = None
    father_name: str
    display_name: str
    append_to_author_name: str
    commentary_text: str
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
    vote_count: int
    note: str
    target_start_verse_id: int
    target_end_verse_id: int
    preview_text: str


class CrossReferenceVerse(APIModel):
    verse_id: int
    book: str
    chapter_number: int
    verse_number: int
    cross_references: list[CrossReferenceItem]


class FootnoteCrossReferenceItem(APIModel):
    reference: str
    reference_note: str
    footnote_id: int
    footnote_label: str
    footnote_text: str
    source_order_number: int | None = None
    target_start_verse_id: int
    target_end_verse_id: int
    preview_text: str


class FootnoteCrossReferenceVerse(APIModel):
    verse_id: int
    book: str
    chapter_number: int
    verse_number: int
    cross_references: list[FootnoteCrossReferenceItem]


class VerseCommentaryResponse(APIModel):
    reference: str
    count: int
    items: list[CommentaryItem]


class VerseCrossReferencesResponse(APIModel):
    reference: str
    verses: list[CrossReferenceVerse]
    footnote_verses: list[FootnoteCrossReferenceVerse]


class SearchIntentEnum(str, Enum):
    REFERENCE = "reference"
    TEXT = "text"


class VerseSearchResult(APIModel):
    result_order: int
    verse_id: int
    reference: str
    book: str
    chapter_number: int
    verse_number: int
    available_translations: list[str] = Field(default_factory=list)
    translation: str
    plain_text: str
    marked_text: str | None = None
    text: str


class VerseNavigationTarget(APIModel):
    kind: str
    reference: str
    label: str


class VerseQueryResponse(APIModel):
    intent: SearchIntentEnum
    query: str
    reference: str | None = None
    scope: str | None = None
    previous_target: VerseNavigationTarget | None = None
    expand_target: VerseNavigationTarget | None = None
    next_target: VerseNavigationTarget | None = None
    verses: list[VerseSearchResult] = Field(default_factory=list)


class VerseTextSearchResponse(APIModel):
    query: str
    page: int
    total: int
    results: list[VerseSearchResult]


class VerseTranslationsResponse(APIModel):
    translations: list[str] = Field(default_factory=list)


class VerseNote(APIModel):
    note_id: int | None = None
    verse: BibleVerse | None = None
    verse_id: int | None = None
    note_markdown: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PartialVerseNote(APIModel):
    verse_id: int | None = None
    note_markdown: str | None = None


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
