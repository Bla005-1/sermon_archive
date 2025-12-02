from rest_framework import serializers

from .models import (
    Attachment,
    BibleBook,
    BibleVerse,
    Sermon,
    SermonPassage,
)


class BibleBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = BibleBook
        fields = ["book_id", "name", "order_num", "testament"]


class BibleVerseSerializer(serializers.ModelSerializer):
    book = BibleBookSerializer(read_only=True)

    class Meta:
        model = BibleVerse
        fields = ["verse_id", "book", "chapter", "verse"]


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attachment
        fields = [
            "attachment_id",
            "sermon",
            "rel_path",
            "original_filename",
            "mime_type",
            "byte_size",
            "created_at",
        ]
        read_only_fields = ["attachment_id", "sermon", "rel_path", "created_at"]


class SermonPassageSerializer(serializers.ModelSerializer):
    start_verse = BibleVerseSerializer(read_only=True)
    end_verse = BibleVerseSerializer(read_only=True)
    start_verse_id = serializers.PrimaryKeyRelatedField(
        queryset=BibleVerse.objects.all(), source="start_verse", write_only=True
    )
    end_verse_id = serializers.PrimaryKeyRelatedField(
        queryset=BibleVerse.objects.all(),
        source="end_verse",
        allow_null=True,
        required=False,
        write_only=True,
    )

    class Meta:
        model = SermonPassage
        fields = [
            "id",
            "sermon",
            "start_verse",
            "end_verse",
            "start_verse_id",
            "end_verse_id",
            "ref_text",
            "context_note",
            "ord",
        ]
        read_only_fields = ["id", "sermon", "start_verse", "end_verse", "ord"]


class SermonSerializer(serializers.ModelSerializer):
    passages = SermonPassageSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Sermon
        fields = [
            "sermon_id",
            "preached_on",
            "title",
            "speaker_name",
            "series_name",
            "location_name",
            "notes_md",
            "created_at",
            "updated_at",
            "passages",
            "attachments",
        ]
        read_only_fields = ["sermon_id", "created_at", "updated_at"]
