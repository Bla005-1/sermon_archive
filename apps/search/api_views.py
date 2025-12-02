from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sermons.models import Sermon
from apps.sermons.serializers import SermonSerializer
from apps.sermons.utils.reference_parser import tolerant_parse_reference, format_ref
from apps.sermons.serializers import BibleVerseSerializer


class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        sermons = Sermon.objects.none()
        if query:
            sermons = Sermon.objects.filter(title__icontains=query).order_by("-preached_on")[:10]
        data = {"sermons": SermonSerializer(sermons, many=True).data}
        return Response(data)


class ReferenceSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "Provide a reference in the 'q' query param."}, status=400)
        try:
            start, end = tolerant_parse_reference(query)
        except Exception as exc:  # pragma: no cover
            return Response({"detail": str(exc)}, status=400)
        payload = {
            "reference": format_ref(start, end),
            "start": BibleVerseSerializer(start).data,
            "end": BibleVerseSerializer(end).data,
        }
        return Response(payload)
