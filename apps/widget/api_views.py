from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from apps.sermons.models import BibleWidgetVerse
from .serializers import BibleWidgetSerializer


class BibleWidgetViewSet(viewsets.ModelViewSet):
    serializer_class = BibleWidgetSerializer
    permission_classes = [IsAuthenticated]
    queryset = BibleWidgetVerse.objects.select_related(
        "start_verse__book", "end_verse__book"
    ).all()
