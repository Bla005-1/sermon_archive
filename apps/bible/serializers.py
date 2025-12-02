from rest_framework import serializers

from apps.sermons.models import BibleVerse, VerseNote
from apps.sermons.serializers import BibleVerseSerializer


class VerseNoteSerializer(serializers.ModelSerializer):
    verse = BibleVerseSerializer(read_only=True)
    verse_id = serializers.PrimaryKeyRelatedField(
        queryset=BibleVerse.objects.all(), source="verse", write_only=True
    )

    class Meta:
        model = VerseNote
        fields = ["note_id", "verse", "verse_id", "note_md", "created_at", "updated_at"]
        read_only_fields = ["note_id", "created_at", "updated_at", "verse"]
