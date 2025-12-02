from rest_framework import serializers

from apps.sermons.models import BibleVerse, BibleWidgetVerse
from apps.sermons.serializers import BibleVerseSerializer


class BibleWidgetSerializer(serializers.ModelSerializer):
    start_verse = BibleVerseSerializer(read_only=True)
    end_verse = BibleVerseSerializer(read_only=True)
    start_verse_id = serializers.PrimaryKeyRelatedField(
        queryset=BibleVerse.objects.all(), source="start_verse", write_only=True
    )
    end_verse_id = serializers.PrimaryKeyRelatedField(
        queryset=BibleVerse.objects.all(), source="end_verse", write_only=True
    )

    class Meta:
        model = BibleWidgetVerse
        fields = [
            "id",
            "start_verse",
            "end_verse",
            "start_verse_id",
            "end_verse_id",
            "translation",
            "ref",
            "display_text",
            "weight",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "start_verse", "end_verse"]
