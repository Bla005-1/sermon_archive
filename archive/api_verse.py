from typing import List, Optional
from ninja import NinjaAPI, Schema
from django.http import Http404
from .utils.reference_parser import build_api_verse_response, tolerant_parse_reference
from .models import BibleWidgetVerse
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


class CommentaryItem(Schema):
    commentary_id: int
    father_id: int
    father_name: str
    display_name: str
    append_to_author_name: Optional[str]
    text: str
    start_verse_id: int
    end_verse_id: int
    reference: str
    source_url: Optional[str]
    source_title: Optional[str]
    default_year: Optional[int]
    wiki_url: Optional[str]

class VerseOut(Schema):
    verse_id: int
    book: str
    chapter: int
    verse: int
    translation: str
    text: Optional[str]
    notes: List[VerseNoteOut]
    cross_refs: List[CrossRefItem]
    commentaries: List[CommentaryItem]
    commentary_count: int

class VerseResponse(Schema):
    query: dict
    parsed_ref: str
    verse_text: str
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


class BibleWidgetOut(Schema):
    id: int
    start_verse_id: int
    end_verse_id: int
    translation: str
    ref: str
    display_text: Optional[str]
    weight: int
    created_at: str
    updated_at: str


@api.get('/biblewidget', response=List[BibleWidgetOut])
def biblewidget_list(request):
    """Return all BibleWidget verses as a simple JSON list."""
    verses = BibleWidgetVerse.objects.all().order_by('-weight', 'id')
    return [
        BibleWidgetOut(
            id=v.id,
            start_verse_id=v.start_verse.verse_id,
            end_verse_id=v.end_verse.verse_id,
            translation=v.translation,
            ref=v.ref,
            display_text=v.display_text,
            weight=v.weight,
            created_at=str(v.created_at),
            updated_at=str(v.updated_at),
        )
        for v in verses
    ]
