from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from django.db.models import Case, IntegerField, Value, When, F
from django.db.models.functions import RowNumber
from django.db.models.expressions import Window

from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bible.models import VerseText
from apps.bible.serializers import BibleVerseSerializer
from apps.bible.utils.reference_parser import format_ref, tolerant_parse_reference
from apps.sermons.models import Sermon
from apps.sermons.serializers import SermonSerializer


def _parse_bool(value: str) -> bool:
    return value.lower() in ("true", "1", "yes", "on")


class SermonSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Search sermons by title.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Full or partial sermon title to search for.",
            )
        ],
        responses={
            200: inline_serializer(
                name="SermonSearchResponse",
                fields={"sermons": SermonSerializer(many=True)},
            )
        },
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        sermons = Sermon.objects.none()
        if query:
            sermons = Sermon.objects.filter(title__icontains=query).order_by("-preached_on")[:10]
        data = {"sermons": SermonSerializer(sermons, many=True).data}
        return Response(data)


class VerseSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Full-text Bible verse search with pagination and optional filters.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Free-text query to search for within verse text.",
                required=True,
            ),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Result page to return (1-indexed).",
            ),
            OpenApiParameter(
                name="book",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Restrict results to a specific Bible book.",
            ),
            OpenApiParameter(
                name="chapter",
                type=int,
                location=OpenApiParameter.QUERY,
                description="Restrict results to a specific chapter within the selected book.",
            ),
            OpenApiParameter(
                name="testament",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Restrict results to OT or NT.",
            ),
            OpenApiParameter(
                name="exact",
                type=bool,
                location=OpenApiParameter.QUERY,
                description="If true, only return verses containing the exact query string.",
            ),
            OpenApiParameter(
                name="translation",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Translation code to search within (defaults to ESV).",
            ),
        ],
        responses={
            200: inline_serializer(
                name="VerseSearchResponse",
                fields={
                    "type": serializers.ChoiceField(choices=["text_results"]),
                    "query": serializers.CharField(),
                    "page": serializers.IntegerField(),
                    "total": serializers.IntegerField(),
                    "results": serializers.ListSerializer(
                        child=inline_serializer(
                            name="VerseSearchResult",
                            fields={
                                "order_num": serializers.IntegerField(),
                                "verse_id": serializers.IntegerField(),
                                "reference": serializers.CharField(),
                                "book": serializers.CharField(),
                                "chapter": serializers.IntegerField(),
                                "verse": serializers.IntegerField(),
                                "translation": serializers.CharField(),
                                "text": serializers.CharField(),
                            },
                        )
                    ),
                },
            ),
            400: OpenApiResponse(description="Missing or invalid query."),
        },
    )
    def get(self, request):
        query = (request.query_params.get("q") or "").strip()
        if not query:
            return Response({"detail": "Provide a search query in the 'q' query param."}, status=400)

        translation = (request.query_params.get("translation") or "").strip()
        page_raw = request.query_params.get("page") or "1"
        try:
            page = max(int(page_raw), 1)
        except ValueError:
            page = 1
        book_filter = (request.query_params.get("book") or "").strip()
        testament = (request.query_params.get("testament") or "").strip().upper()
        chapter_raw = request.query_params.get("chapter")
        try:
            chapter = int(chapter_raw) if chapter_raw is not None else None
        except ValueError:
            chapter = None
        exact = _parse_bool(request.query_params.get("exact", "false"))

        page_size = 20
        qs = VerseText.objects.select_related("verse__book", "verse")
        if translation:
            qs = qs.filter(translation__iexact=translation)
        if book_filter:
            qs = qs.filter(verse__book__name__iexact=book_filter)
        if testament in ("OT", "NT"):
            qs = qs.filter(verse__book__testament=testament)
        if chapter is not None:
            qs = qs.filter(verse__chapter=chapter)

        search_terms = [query] if exact else [term for term in query.split() if term]
        if not search_terms:
            return Response({"detail": "Provide a non-empty search query."}, status=400)
        for term in search_terms:
            qs = qs.filter(plain_text__icontains=term)

        match_components = [
            Case(
                When(plain_text__icontains=term, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            )
            for term in search_terms
        ]
        match_baseline = Value(0, output_field=IntegerField())
        qs = qs.annotate(
            starts_with=Case(
                When(plain_text__istartswith=query, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            esv_preference=Case(
                When(translation__iexact="ESV", then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            match_count=sum(match_components, match_baseline) if match_components else match_baseline,
        ).order_by(
            "-starts_with",
            "-match_count",
            "verse__book__order_num",
            "verse__chapter",
            "verse__verse",
        )
        if not translation:
            qs = qs.annotate(
                row_number=Window(
                    expression=RowNumber(),
                    partition_by=[F("verse_id")],
                    order_by=[
                        F("starts_with").desc(),
                        F("match_count").desc(),
                        F("esv_preference").desc(),  # ← ESV wins ties
                    ],
                )
            ).filter(row_number=1)
            
        total = qs.count()
        offset = (page - 1) * page_size
        results = list(qs[offset : offset + page_size])

        payload = {
            "type": "text_results",
            "query": query,
            "page": page,
            "total": total,
            "results": [],
        }

        for idx, row in enumerate(results):
            verse = row.verse
            payload["results"].append(
                {
                    "order_num": offset + idx + 1,
                    "verse_id": verse.verse_id,
                    "reference": format_ref(verse, verse),
                    "book": verse.book.name,
                    "chapter": verse.chapter,
                    "verse": verse.verse,
                    "translation": row.translation,
                    "text": row.plain_text,
                }
            )

        return Response(payload)


class ReferenceSearchView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Resolve a Bible reference into canonical start/end verses.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Reference string such as "1 John 4" or "John 3:16-18".',
            )
        ],
        responses={
            200: inline_serializer(
                name="ReferenceSearchResponse",
                fields={
                    "reference": serializers.CharField(),
                    "start": BibleVerseSerializer(),
                    "end": BibleVerseSerializer(),
                },
            ),
            400: OpenApiResponse(description="The provided reference could not be parsed."),
        },
    )
    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "Provide a reference in the 'q' query param."}, status=400)
        try:
            start, end = tolerant_parse_reference(query)
        except Exception as exc:  # pragma: no cover
            return Response({"detail": str(exc)}, status=400)
        try:
            reference = format_ref(start, end)
        except Exception:
            reference = ""
        payload = {
            "reference": reference,
            "start": BibleVerseSerializer(start).data,
            "end": BibleVerseSerializer(end).data,
        }
        return Response(payload)
