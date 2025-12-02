from rest_framework import serializers

from apps.bible.models import BibleVerse
from apps.bible.serializers import BibleVerseSerializer
from apps.sermons.models import BibleWidgetVerse


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
