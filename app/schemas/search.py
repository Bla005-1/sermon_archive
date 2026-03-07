from enum import Enum

from app.schemas.base import APIModel
from app.schemas.sermons import Sermon
from app.schemas.verses import BibleVerse


class VerseSearchResponseTypeEnum(str, Enum):
    TEXT_RESULTS = "text_results"


class VerseSearchResult(APIModel):
    order_num: int
    verse_id: int
    reference: str
    book: str
    chapter: int
    verse: int
    translation: str
    text: str


class VerseSearchResponse(APIModel):
    type: VerseSearchResponseTypeEnum
    query: str
    page: int
    total: int
    results: list[VerseSearchResult]


class ReferenceSearchResponse(APIModel):
    reference: str
    start: BibleVerse
    end: BibleVerse


class SermonSearchResponse(APIModel):
    sermons: list[Sermon]
