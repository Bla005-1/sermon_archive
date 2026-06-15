from __future__ import annotations

from enum import Enum

from sermon_archive.schemas.base import APIModel
from sermon_archive.schemas.verses import BibleVerse


class ScriptureReferenceSourceType(str, Enum):
    library_item_unit = "library_item_unit"
    sermon = "sermon"


class ScriptureReference(APIModel):
    scripture_reference_id: int | None = None
    source_type: ScriptureReferenceSourceType
    source_id: int
    start_verse: BibleVerse | None = None
    end_verse: BibleVerse | None = None
    start_verse_id: int
    end_verse_id: int | None = None
    reference_text: str
    matched_text: str
    context_text: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    display_order: int | None = None


class UnresolvedScriptureReference(APIModel):
    matched_text: str
    reason: str
    context_text: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None


class ScriptureExtractionRequest(APIModel):
    text: str
    context_text: str | None = None
    source_type: ScriptureReferenceSourceType | None = None
    source_id: int | None = None


class ScriptureExtractionResponse(APIModel):
    references: list[ScriptureReference]
    unresolved: list[UnresolvedScriptureReference] = []
