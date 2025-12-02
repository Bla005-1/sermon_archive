from rest_framework import status
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.sermons.models import BibleVerse, VerseNote
from apps.sermons.serializers import BibleVerseSerializer
from apps.sermons.utils.reference_parser import format_ref, tolerant_parse_reference

from .serializers import VerseNoteSerializer


class BibleLookupView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"detail": "Provide a reference in the 'q' query param."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            start, end = tolerant_parse_reference(query)
        except Exception as exc:  # pragma: no cover - passthrough from parser
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        data = {
            "start": BibleVerseSerializer(start).data,
            "end": BibleVerseSerializer(end).data,
            "reference": format_ref(start, end),
        }
        return Response(data)


class VerseNoteListCreateView(ListCreateAPIView):
    serializer_class = VerseNoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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
