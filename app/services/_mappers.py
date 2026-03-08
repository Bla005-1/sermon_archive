"""ORM-to-schema mapping helpers used by service functions."""

from __future__ import annotations

from app.db.models import (
    Attachments,
    BibleBooks,
    BibleVerses,
    BibleWidgetVerses,
    SermonPassages,
    Sermons,
    VerseNotes,
)
from app.schemas.attachments import Attachment
from app.schemas.sermons import Sermon, SermonPassage
from app.schemas.verses import BibleBook, BibleVerse, VerseNote, TestamentEnum
from app.schemas.widget import BibleWidget


def bible_book_schema(book: BibleBooks) -> BibleBook:
    """Convert a BibleBooks ORM row into a BibleBook schema object."""
    return BibleBook(
        book_id=book.book_id,
        name=book.name,
        order_num=book.order_num,
        testament=TestamentEnum[book.testament.value],
    )


def bible_verse_schema(verse: BibleVerses) -> BibleVerse:
    """Convert a BibleVerses ORM row into a BibleVerse schema object."""
    return BibleVerse(
        verse_id=verse.verse_id,
        book=bible_book_schema(verse.book),
        chapter=verse.chapter,
        verse=verse.verse,
    )


def attachment_schema(attachment: Attachments) -> Attachment:
    """Convert an Attachments ORM row into an Attachment schema object."""
    return Attachment(
        attachment_id=attachment.attachment_id,
        sermon=attachment.sermon_id,
        rel_path=attachment.rel_path,
        original_filename=attachment.original_filename,
        mime_type=attachment.mime_type,
        byte_size=attachment.byte_size,
        created_at=attachment.created_at,
    )


def sermon_passage_schema(passage: SermonPassages) -> SermonPassage:
    """Convert a SermonPassages ORM row into a SermonPassage schema object."""
    return SermonPassage(
        id=passage.id,
        sermon=passage.sermon_id,
        start_verse=bible_verse_schema(passage.start_verse),
        end_verse=bible_verse_schema(passage.end_verse) if passage.end_verse else None,
        start_verse_id=passage.start_verse_id,
        end_verse_id=passage.end_verse_id,
        ref_text=passage.ref_text,
        context_note=passage.context_note,
        ord=passage.ord,
    )


def sermon_schema(sermon: Sermons, *, include_nested: bool = True) -> Sermon:
    """Convert a Sermons ORM row into a Sermon schema object."""
    passages = []
    attachments = []
    if include_nested:
        attachments = [
            attachment_schema(item) for item in getattr(sermon, "attachments", [])
        ]
        passages = [
            sermon_passage_schema(item)
            for item in getattr(sermon, "sermon_passages", [])
        ]
        passages.sort(key=lambda item: ((item.ord or 0), item.id or 0))

    return Sermon(
        sermon_id=sermon.sermon_id,
        preached_on=sermon.preached_on,
        title=sermon.title,
        speaker_name=sermon.speaker_name,
        series_name=sermon.series_name,
        location_name=sermon.location_name,
        notes_md=sermon.notes_md,
        created_at=sermon.created_at,
        updated_at=sermon.updated_at,
        passages=passages,
        attachments=attachments,
    )


def verse_note_schema(note: VerseNotes) -> VerseNote:
    """Convert a VerseNotes ORM row into a VerseNote schema object."""
    return VerseNote(
        note_id=note.note_id,
        verse=bible_verse_schema(note.verse),
        verse_id=note.verse_id,
        note_md=note.note_md,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def widget_schema(widget: BibleWidgetVerses) -> BibleWidget:
    """Convert a BibleWidgetVerses ORM row into a BibleWidget schema object."""
    return BibleWidget(
        id=widget.id,
        start_verse=bible_verse_schema(widget.start_verse),
        end_verse=bible_verse_schema(widget.end_verse),
        start_verse_id=widget.start_verse_id,
        end_verse_id=widget.end_verse_id,
        translation=widget.translation,
        ref=widget.ref,
        display_text=widget.display_text,
        weight=widget.weight,
        created_at=widget.created_at,
        updated_at=widget.updated_at,
    )
