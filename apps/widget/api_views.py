from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.sermons.models import BibleWidgetVerse
from .serializers import BibleWidgetCreateSerializer, BibleWidgetSerializer


class BibleWidgetViewSet(viewsets.ModelViewSet):
    serializer_class = BibleWidgetSerializer
    permission_classes = [IsAuthenticated]
    queryset = BibleWidgetVerse.objects.select_related(
        "start_verse__book", "end_verse__book"
    ).all()

    @action(detail=False, methods=["post"], url_path="create")
    def create_widget(self, request):
        request_serializer = BibleWidgetCreateSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        verse_ids = request_serializer.validated_data["verse_ids"]
        start_verse_id = verse_ids[0]
        end_verse_id = verse_ids[-1]
        translation = request_serializer.validated_data["translation"]

        entry, created = BibleWidgetVerse.objects.update_or_create(
            start_verse_id=start_verse_id,
            end_verse_id=end_verse_id,
            translation=translation,
            defaults={
                "ref": request_serializer.validated_data["reference"],
                "display_text": request_serializer.validated_data["display_text"],
            },
        )
        response_serializer = self.get_serializer(entry)
        response_status = status.HTTP_201_CREATED if created else status.HTTP_200_OK
        return Response(response_serializer.data, status=response_status)
