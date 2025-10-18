from typing import List, Optional
from ninja import NinjaAPI, Schema
from django.http import Http404
from .utils.reference_parser import build_api_verse_response, tolerant_parse_reference
api = NinjaAPI()

class VerseNoteOut(Schema):
    note_id: int
    note_md: Optional[str]
    created_at: str
    updated_at: str

class CrossRefItem(Schema):
    reference: str          # 'John 3:16–18'
    to_start_id: int
    to_end_id: int
    preview_text: Optional[str] = None
    votes: int
    note: str

class VerseOut(Schema):
    verse_id: int
    book: str
    chapter: int
    verse: int
    translation: str
    text: Optional[str]
    notes: List[VerseNoteOut]
    cross_refs: List[CrossRefItem]

class VerseResponse(Schema):
    query: dict
    count: int
    results: List[VerseOut]


@api.get('/verse', response=VerseResponse)
def verse_lookup(request, ref: str, translation: Optional[str] = 'ESV'):
    try:
        tolerant_parse_reference(ref)
    except ValueError as e:
        raise Http404(str(e))

    payload = build_api_verse_response(ref, translation_hint=translation)
    return payload
