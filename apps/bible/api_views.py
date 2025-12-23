from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.request import Request
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from typing import Dict, List, Sequence, Tuple
from apps.bible.models import BibleVerse, VerseNote, VerseText
from apps.bible.utils.reference_parser import (
    build_commentary_context,
    determine_available_translations,
    format_ref,
    get_crossrefs_from,
    join_passage_text,
    select_default_translation,
    tolerant_parse_reference,
)
from .serializers import VerseNoteSerializer


def _parse_reference(ref_text: str):
    try:
        start, end = tolerant_parse_reference(ref_text)
        return start, end
    except Exception as e:  # pragma: no cover - parser raises helpful errors
        raise e


def _load_passage_verses(start: BibleVerse, end: BibleVerse):
    return list(
        BibleVerse.objects.select_related("book")
        .filter(
            book=start.book,
            chapter=start.chapter,
            verse__gte=start.verse,
            verse__lte=end.verse,
        )
        .order_by("verse")
    )


def _select_translation(
    verses: Sequence[BibleVerse], translation_hint: str
) -> Tuple[str, Dict[str, Dict[int, str]], Dict[str, Dict[int, str]], List[str]]:
    verse_ids = [v.verse_id for v in verses]
    translation_map: Dict[str, Dict[int, str]] = {}
    marked_translation_map: Dict[str, Dict[int, str]] = {}
    for vt in VerseText.objects.filter(verse__in=verses):
        translation_map.setdefault(vt.translation, {})[vt.verse.verse_id] = vt.plain_text
        marked_translation_map.setdefault(vt.translation, {})[vt.verse.verse_id] = vt.marked_text
    available = determine_available_translations(verse_ids, translation_map)
    selected = translation_hint if translation_hint in available else select_default_translation(available)
    if not selected and available:
        selected = available[0]
    return selected or "ESV", translation_map, marked_translation_map, available


def _preview_text_for_range(to_start_id: int, to_end_id: int) -> str:
    a, b = (min(to_start_id, to_end_id), max(to_start_id, to_end_id))
    rng = list(
        BibleVerse.objects.select_related("book")
        .filter(verse_id__gte=a, verse_id__lte=b)
        .order_by("verse_id")
    )
    if not rng:
        return ""
    rows = list(
        VerseText.objects.filter(verse__in=rng, translation="ESV").order_by("verse__verse")
    )
    if not rows:
        rows = list(
            VerseText.objects.filter(verse__in=rng).order_by("translation", "verse__verse")
        )
    lookup: Dict[int, str] = {}
    for vt in rows:
        lookup.setdefault(vt.verse.verse_id, vt.plain_text)
    plain_text, _ = join_passage_text(rng, lookup)
    return plain_text


class VersePassageView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Retrieve a passage with verse text, notes, and available translations. "
        "If the provided query is not a Bible reference, a lightweight intent payload is returned instead of performing any lookup.",
        parameters=[
            OpenApiParameter(
                name="query",
                type=str,
                location=OpenApiParameter.QUERY,
                description='Bible reference such as "John 3:16-18" or "Psalm 23". Also accepts "ref" for backwards compatibility.',
                required=True,
            ),
            OpenApiParameter(
                name="translation",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Preferred translation code (e.g., ESV, NIV). Defaults to ESV.",
                required=False,
            ),
        ],
        responses={
            200: inline_serializer(
                name="VersePassageResponse",
                fields={
                    "type": serializers.ChoiceField(choices=["reference"]),
                    "reference": serializers.CharField(),
                    "translation": serializers.CharField(),
                    "text": serializers.CharField(),
                    "combined_marked_text": serializers.CharField(),
                    "verses": serializers.ListSerializer(
                        child=inline_serializer(
                            name="PassageVerse",
                            fields={
                                "verse_id": serializers.IntegerField(),
                                "book": serializers.CharField(),
                                "chapter": serializers.IntegerField(),
                                "verse": serializers.IntegerField(),
                                "text": serializers.CharField(),
                                "marked_text": serializers.CharField(),
                                "translation": serializers.CharField(),
                                "notes": serializers.CharField(allow_null=True, required=False),
                            },
                        )
                    ),
                    "available_translations": serializers.ListSerializer(
                        child=serializers.CharField()
                    ),
                },
            ),
            200: inline_serializer(
                name="VerseIntentResponse",
                fields={
                    "type": serializers.ChoiceField(choices=["text"]),
                    "query": serializers.CharField(),
                },
            ),
            400: OpenApiResponse(description="Missing reference."),
        },
    )
    def get(self, request):
        reference = (
            request.query_params.get("query")
            or request.query_params.get("ref")
            or ""
        ).strip()
        translation_hint = (request.query_params.get("translation") or "ESV").strip()
        if not reference:
            return Response(
                {"detail": "Provide a reference in the 'query' query param."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start, end = _parse_reference(reference)
        except ValueError:
            return Response({"type": "text", "query": reference})
        except Exception as e:
            return Response({"detail": e}, status=status.HTTP_400_BAD_REQUEST)

        verses = _load_passage_verses(start, end)
        if not verses:
            return Response({"detail": "No verses found for the given reference."}, status=status.HTTP_404_NOT_FOUND)

        selected_translation, translation_map, marked_translation_map, available_translations = _select_translation(
            verses,
            translation_hint,
        )
        verse_lookup = translation_map.get(selected_translation, {})
        verse_marked_lookup = marked_translation_map.get(selected_translation, {})
        combined_text, _ = join_passage_text(verses, verse_lookup)
        combined_marked_text, _ = join_passage_text(verses, verse_marked_lookup)

        notes_by_vid: dict[int, str] = {}
        for note in VerseNote.objects.filter(verse__in=verses).order_by("created_at"):
            if note.note_md:
                notes_by_vid.setdefault(note.verse.verse_id, note.note_md)
        verse_payload = []
        for verse in verses:
            verse_payload.append(
                {
                    "verse_id": verse.verse_id,
                    "book": verse.book.name,
                    "chapter": verse.chapter,
                    "verse": verse.verse,
                    "text": verse_lookup.get(verse.verse_id, ""),
                    "marked_text": verse_marked_lookup.get(verse.verse_id, ""),
                    "translation": selected_translation,
                    "notes": notes_by_vid.get(verse.verse_id),
                }
            )
        available_translations = [name.upper() for name in available_translations]
        return Response(
            {
                "type": "reference",
                "reference": format_ref(start, end),
                "translation": selected_translation,
                "text": combined_text,
                "combined_marked_text": combined_marked_text,
                "verses": verse_payload,
                "available_translations": available_translations,
            }
        )


class VerseCrossReferenceView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Return cross references for the requested verse or passage.",
        parameters=[
            OpenApiParameter(
                name="ref",
                type=str,
                location=OpenApiParameter.QUERY,
                description='Bible reference such as "Romans 8:28".',
                required=True,
            )
        ],
        responses={
            200: inline_serializer(
                name="VerseCrossReferencesResponse",
                fields={
                    "reference": serializers.CharField(),
                    "verses": serializers.ListSerializer(
                        child=inline_serializer(
                            name="CrossReferenceVerse",
                            fields={
                                "verse_id": serializers.IntegerField(),
                                "book": serializers.CharField(),
                                "chapter": serializers.IntegerField(),
                                "verse": serializers.IntegerField(),
                                "cross_references": serializers.ListSerializer(
                                    child=inline_serializer(
                                        name="CrossReferenceItem",
                                        fields={
                                            "reference": serializers.CharField(),
                                            "votes": serializers.IntegerField(),
                                            "note": serializers.CharField(),
                                            "to_start_id": serializers.IntegerField(),
                                            "to_end_id": serializers.IntegerField(),
                                            "preview_text": serializers.CharField(),
                                        },
                                    )
                                ),
                            },
                        )
                    ),
                },
            ),
            400: OpenApiResponse(description="Missing or invalid reference."),
        },
    )
    def get(self, request):
        reference = (request.query_params.get("ref") or "").strip()
        if not reference:
            return Response(
                {"detail": "Provide a reference in the 'ref' query param."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start, end = _parse_reference(reference)
        except Exception as e:
            return Response({"detail": e}, status=status.HTTP_400_BAD_REQUEST)

        verses = _load_passage_verses(start, end)
        crossrefs = get_crossrefs_from(verses)
        payload = []
        for verse in verses:
            items = []
            for cr in crossrefs.get(verse.verse_id, []):
                preview = _preview_text_for_range(cr["to_start_id"], cr["to_end_id"])
                items.append({**cr, "preview_text": preview})
            payload.append(
                {
                    "verse_id": verse.verse_id,
                    "book": verse.book.name,
                    "chapter": verse.chapter,
                    "verse": verse.verse,
                    "cross_references": items,
                }
            )

        return Response({"reference": format_ref(start, end), "verses": payload})


class VerseCommentaryView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Return patristic commentary excerpts for the requested verse or passage.",
        parameters=[
            OpenApiParameter(
                name="ref",
                type=str,
                location=OpenApiParameter.QUERY,
                description='Bible reference such as "Genesis 1".',
                required=True,
            )
        ],
        responses={
            200: inline_serializer(
                name="VerseCommentaryResponse",
                fields={
                    "reference": serializers.CharField(),
                    "count": serializers.IntegerField(),
                    "items": serializers.ListSerializer(
                        child=inline_serializer(
                            name="CommentaryItem",
                            fields={
                                "commentary_id": serializers.IntegerField(),
                                "father_id": serializers.IntegerField(allow_null=True, required=False),
                                "father_name": serializers.CharField(allow_blank=True),
                                "display_name": serializers.CharField(),
                                "append_to_author_name": serializers.CharField(allow_blank=True),
                                "text": serializers.CharField(),
                                "book_id": serializers.IntegerField(),
                                "start_verse_id": serializers.IntegerField(),
                                "end_verse_id": serializers.IntegerField(),
                                "reference": serializers.CharField(),
                                "source_url": serializers.CharField(allow_blank=True),
                                "source_title": serializers.CharField(allow_blank=True),
                                "default_year": serializers.IntegerField(allow_null=True, required=False),
                                "wiki_url": serializers.CharField(allow_blank=True),
                                "start": inline_serializer(
                                    name="CommentaryStart",
                                    fields={
                                        "book": serializers.CharField(),
                                        "chapter": serializers.IntegerField(),
                                        "verse": serializers.IntegerField(),
                                    },
                                ),
                                "end": inline_serializer(
                                    name="CommentaryEnd",
                                    fields={
                                        "book": serializers.CharField(),
                                        "chapter": serializers.IntegerField(),
                                        "verse": serializers.IntegerField(),
                                    },
                                ),
                            },
                        )
                    ),
                },
            ),
            400: OpenApiResponse(description="Missing or invalid reference."),
        },
    )
    def get(self, request):
        reference = (request.query_params.get("ref") or "").strip()
        if not reference:
            return Response(
                {"detail": "Provide a reference in the 'ref' query param."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            start, end = _parse_reference(reference)
        except Exception as e:
            return Response({"detail": e}, status=status.HTTP_400_BAD_REQUEST)

        verses = _load_passage_verses(start, end)
        commentary_context = build_commentary_context(verses)
        return Response(
            {
                "reference": format_ref(start, end),
                "count": commentary_context.get("count", 0),
                "items": commentary_context.get("items", []),
            }
        )


@extend_schema_view(
    list=extend_schema(
        description="List verse notes, optionally filtered by verse id.",
        parameters=[
            OpenApiParameter(
                name="verse_id",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Filter notes by the verse identifier.",
            )
        ],
    )
)
class VerseNoteListCreateView(ListCreateAPIView):
    serializer_class = VerseNoteSerializer
    permission_classes = [IsAuthenticated]
    request: Request
    
    def get_queryset(self):  # type: ignore
        qs = VerseNote.objects.select_related("verse", "verse__book").all()
        verse_id = self.request.query_params.get("verse_id")
        if verse_id:
            qs = qs.filter(verse_id=verse_id)
        return qs.order_by("-updated_at")


class VerseNoteDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = VerseNoteSerializer
    permission_classes = [IsAuthenticated]
    queryset = VerseNote.objects.select_related("verse", "verse__book").all()
    lookup_field = "note_id"
