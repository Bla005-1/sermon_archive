from django.db import models
from django.utils import timezone


class BibleBook(models.Model):
    book_id = models.AutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=64)
    order_num = models.PositiveIntegerField()

    TESTAMENT_CHOICES = [('OT', 'OT'), ('NT', 'NT')]
    testament = models.CharField(max_length=2, choices=TESTAMENT_CHOICES)

    class Meta:
        managed = False
        db_table = 'bible_books'

    def __str__(self):
        return self.name


class BibleVerse(models.Model):
    verse_id = models.BigAutoField(primary_key=True)
    book = models.ForeignKey(BibleBook, models.DO_NOTHING)
    chapter = models.PositiveSmallIntegerField()
    verse = models.PositiveSmallIntegerField()

    class Meta:
        managed = False
        db_table = 'bible_verses'
        unique_together = (('book', 'chapter', 'verse'),)

    def __str__(self):
        return f'{self.book.name} {self.chapter}:{self.verse}'


class VerseText(models.Model):
    verse_text_id = models.BigAutoField(primary_key=True)
    verse = models.ForeignKey(BibleVerse, models.DO_NOTHING)
    translation = models.CharField(max_length=16)
    plain_text = models.TextField()
    marked_text = models.TextField()

    class Meta:
        managed = False
        db_table = 'verse_texts_marked'
        unique_together = (('verse', 'translation'),)


class VerseNote(models.Model):
    note_id = models.BigAutoField(primary_key=True)
    verse = models.ForeignKey(BibleVerse, models.DO_NOTHING)
    note_md = models.TextField(blank=True, null=True)
    # Avoid NULL on insert from Django; DB has defaults.
    created_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    updated_at = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'verse_notes'


class VerseCrossReference(models.Model):
    id = models.BigAutoField(primary_key=True)
    from_verse = models.ForeignKey(BibleVerse, models.DO_NOTHING, related_name='cross_references')
    to_start_verse = models.ForeignKey(
        BibleVerse,
        models.DO_NOTHING,
        related_name='cross_reference_sources_start',
    )
    to_end_verse = models.ForeignKey(
        BibleVerse,
        models.DO_NOTHING,
        related_name='cross_reference_sources_end',
        blank=True,
        null=True,
    )
    votes = models.IntegerField(blank=True, null=True)
    note = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'verse_crossrefs'
        unique_together = (('from_verse', 'to_start_verse', 'to_end_verse'),)


class ChurchFather(models.Model):
    father_id = models.BigAutoField(primary_key=True)
    name = models.CharField(unique=True, max_length=128)
    default_year = models.IntegerField(blank=True, null=True)
    wiki_url = models.CharField(max_length=512, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'church_fathers'

    def __str__(self):  # pragma: no cover - trivial string formatting
        return self.name


class Commentary(models.Model):
    commentary_id = models.BigAutoField(primary_key=True)
    father = models.ForeignKey(ChurchFather, models.DO_NOTHING)
    append_to_author_name = models.CharField(max_length=255, blank=True, null=True)
    book = models.ForeignKey(BibleBook, models.DO_NOTHING)
    start_verse = models.ForeignKey(
        BibleVerse,
        models.DO_NOTHING,
        related_name='commentary_start_entries',
    )
    end_verse = models.ForeignKey(
        BibleVerse,
        models.DO_NOTHING,
        related_name='commentary_end_entries',
    )
    txt = models.TextField()
    source_url = models.CharField(max_length=2048, blank=True, null=True)
    source_title = models.CharField(max_length=512, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'commentaries'

    def __str__(self):  # pragma: no cover - trivial string formatting
        author = self.father.name if self.father.father_id else 'Commentary'
        return f'{author} on {self.book.name}'
