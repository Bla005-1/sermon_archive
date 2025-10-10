# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Attachment(models.Model):
    attachment_id = models.BigAutoField(primary_key=True)
    sermon = models.ForeignKey('Sermon', models.DO_NOTHING)
    rel_path = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255, blank=True, null=True)
    mime_type = models.CharField(max_length=64, blank=True, null=True)
    byte_size = models.PositiveBigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'attachments'


class BibleBook(models.Model):
    book_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=64)
    order_num = models.PositiveIntegerField()
    testament = models.CharField(max_length=2)

    class Meta:
        managed = False
        db_table = 'bible_books'


class BibleVerse(models.Model):
    verse_id = models.BigAutoField(primary_key=True)
    book = models.ForeignKey(BibleBook, models.DO_NOTHING)
    chapter = models.PositiveSmallIntegerField()
    verse = models.PositiveSmallIntegerField()

    class Meta:
        managed = False
        db_table = 'bible_verses'


class Illustration(models.Model):
    illustration_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=256)
    body_md = models.TextField()
    keywords_csv = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=256, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'illustrations'


class SermonIllustration(models.Model):
    pk = models.CompositePrimaryKey('sermon_id', 'illustration_id')
    sermon = models.ForeignKey('Sermon', models.DO_NOTHING)
    illustration = models.ForeignKey(Illustration, models.DO_NOTHING)
    ord = models.PositiveSmallIntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sermon_illustrations'


class SermonPassage(models.Model):
    pk = models.CompositePrimaryKey('sermon_id', 'ord')
    sermon = models.ForeignKey('Sermon', models.DO_NOTHING)
    start_verse = models.ForeignKey(BibleVerse, models.DO_NOTHING)
    end_verse = models.ForeignKey(BibleVerse, models.DO_NOTHING, related_name='sermonpassages_end_verse_set', blank=True, null=True)
    ref_text = models.CharField(max_length=64, blank=True, null=True)
    context_note = models.CharField(max_length=512, blank=True, null=True)
    ord = models.PositiveSmallIntegerField()

    class Meta:
        managed = False
        db_table = 'sermon_passages'


class Sermon(models.Model):
    sermon_id = models.BigAutoField(primary_key=True)
    preached_on = models.DateField()
    title = models.CharField(max_length=256)
    speaker_name = models.CharField(max_length=128, blank=True, null=True)
    series_name = models.CharField(max_length=128, blank=True, null=True)
    location_name = models.CharField(max_length=128, blank=True, null=True)
    notes_md = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'sermons'


class VerseNote(models.Model):
    note_id = models.BigAutoField(primary_key=True)
    verse = models.ForeignKey(BibleVerse, models.DO_NOTHING)
    note_md = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'verse_notes'


class VerseText(models.Model):
    verse_text_id = models.BigAutoField(primary_key=True)
    verse = models.ForeignKey(BibleVerse, models.DO_NOTHING)
    translation = models.CharField(max_length=16)
    text = models.TextField()

    class Meta:
        managed = False
        db_table = 'verse_texts'
