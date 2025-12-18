from django.db.models import F
from django.db.models.functions import Coalesce
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bible.utils.reference_parser import format_ref, tolerant_parse_reference
from .models import SermonPassage


def _parse_reference(ref_text: str):
    try:
        start, end = tolerant_parse_reference(ref_text)
        return start, end, None
    except Exception as exc:  # pragma: no cover - parser raises helpful errors
        return None, None, str(exc)


class VerseSermonsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="List sermons that include the requested verse or passage.",
        parameters=[
            OpenApiParameter(
                name="ref",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description='Bible reference such as "Philippians 2:1-11" or "Psalm 23".',
            )
        ],
        responses={
            200: inline_serializer(
                name="VerseSermonResponse",
                fields={
                    "reference": serializers.CharField(),
                    "sermons": serializers.ListSerializer(
                        child=inline_serializer(
                            name="VerseSermonItem",
                            fields={
                                "sermon_id": serializers.IntegerField(),
                                "title": serializers.CharField(),
                                "preached_on": serializers.DateField(
                                    allow_null=True, required=False
                                ),
                                "speaker_name": serializers.CharField(allow_blank=True),
                                "series_name": serializers.CharField(allow_blank=True),
                                "reference": serializers.CharField(),
                                "context_note": serializers.CharField(allow_blank=True),
                                "start_verse_id": serializers.IntegerField(),
                                "end_verse_id": serializers.IntegerField(),
                            },
                        )()
                    ),
                },
            ),
            400: OpenApiResponse(description="Reference missing or could not be parsed."),
        },
    )
    def get(self, request):
        reference = (request.query_params.get("ref") or "").strip()
        if not reference:
            return Response(
                {"detail": "Provide a reference in the 'ref' query param."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start, end, error = _parse_reference(reference)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        query_start = min(start.verse_id, end.verse_id)
        query_end = max(start.verse_id, end.verse_id)

        passages = list(
            SermonPassage.objects.select_related("sermon", "start_verse__book", "end_verse__book")
            .annotate(
                start_id=F("start_verse__verse_id"),
                end_id=Coalesce("end_verse__verse_id", F("start_verse__verse_id")),
            )
            .filter(start_id__lte=query_end, end_id__gte=query_start)
        )

        results = []
        for passage in passages:
            sermon = passage.sermon
            start_id = getattr(passage, "start_id", passage.start_verse.verse_id)
            end_id = getattr(passage, "end_id", passage.end_verse.verse_id if passage.end_verse_id else start_id)
            start_id, end_id = (min(start_id, end_id), max(start_id, end_id))
            length = (end_id - start_id) + 1
            display_ref = passage.ref_text or passage.ref_display()

            if query_start == query_end:
                is_exact = start_id == query_start and end_id == query_end
                boundary_distance = abs(start_id - query_start) + abs(end_id - query_end)
                sort_key = (
                    0 if is_exact else 1,
                    length,
                    boundary_distance,
                    -sermon.preached_on.toordinal() if sermon.preached_on else float("inf"),
                    -sermon.pk,
                )
            else:
                overlap_start = max(start_id, query_start)
                overlap_end = min(end_id, query_end)
                overlap_length = overlap_end - overlap_start + 1 if overlap_end >= overlap_start else 0
                if overlap_length <= 0:
                    continue
                coverage_ratio = overlap_length / ((query_end - query_start) + 1)
                length_diff = abs(length - ((query_end - query_start) + 1))
                start_diff = abs(start_id - query_start)
                end_diff = abs(end_id - query_end)
                coverage_group = 0
                if coverage_ratio < 1:
                    coverage_group = 1 if coverage_ratio >= 0.5 else 2
                if coverage_ratio == 1 and length_diff >= ((query_end - query_start) + 1):
                    coverage_group = max(coverage_group, 1)
                if coverage_ratio < 1 and length_diff >= ((query_end - query_start) + 1):
                    coverage_group = max(coverage_group, 2)
                sort_key = (
                    coverage_group,
                    length_diff,
                    start_diff,
                    end_diff,
                    -sermon.preached_on.toordinal() if sermon.preached_on else float("inf"),
                    -sermon.pk,
                )

            results.append(
                {
                    "sermon_id": sermon.pk,
                    "title": sermon.title,
                    "preached_on": sermon.preached_on,
                    "speaker_name": sermon.speaker_name,
                    "series_name": sermon.series_name,
                    "reference": display_ref,
                    "context_note": passage.context_note or "",
                    "start_verse_id": start_id,
                    "end_verse_id": end_id,
                    "sort_key": sort_key,
                }
            )

        sorted_results = sorted(results, key=lambda r: r["sort_key"])
        for entry in sorted_results:
            entry.pop("sort_key", None)

        return Response({"reference": format_ref(start, end), "sermons": sorted_results})
