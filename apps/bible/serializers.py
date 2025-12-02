from rest_framework import serializers

from apps.bible.models import BibleBook, BibleVerse, VerseNote


class BibleBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = BibleBook
        fields = ["book_id", "name", "order_num", "testament"]


class BibleVerseSerializer(serializers.ModelSerializer):
    book = BibleBookSerializer(read_only=True)

    class Meta:
        model = BibleVerse
        fields = ["verse_id", "book", "chapter", "verse"]


class VerseNoteSerializer(serializers.ModelSerializer):
    verse = BibleVerseSerializer(read_only=True)
    verse_id = serializers.PrimaryKeyRelatedField(
        queryset=BibleVerse.objects.all(), source="verse", write_only=True
    )

    class Meta:
        model = VerseNote
        fields = ["note_id", "verse", "verse_id", "note_md", "created_at", "updated_at"]
        read_only_fields = ["note_id", "created_at", "updated_at", "verse"]
