from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bible.serializers import BibleVerseSerializer
from apps.bible.utils.reference_parser import format_ref, tolerant_parse_reference
from apps.sermons.models import Sermon
from apps.sermons.serializers import SermonSerializer


class SearchView(APIView):
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
