from django.db import models

class Sermon(models.Model):
    preached_on = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=255)
    speaker_name = models.CharField(max_length=255, blank=True)
    series_name = models.CharField(max_length=255, blank=True)
    location_name = models.CharField(max_length=255, blank=True)
    notes_md = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-preached_on', '-id']

    def __str__(self):
        return f'{self.preached_on} — {self.title}'

class BibleBook(models.Model):
    name = models.CharField(max_length=64, unique=True)
    def __str__(self): return self.name

class BibleVerse(models.Model):
    book = models.ForeignKey(BibleBook, on_delete=models.CASCADE)
    chapter = models.IntegerField()
    verse = models.IntegerField()
    class Meta:
        unique_together = ('book', 'chapter', 'verse')
        ordering = ['book_id', 'chapter', 'verse']

class SermonPassage(models.Model):
    sermon = models.ForeignKey(Sermon, on_delete=models.CASCADE, related_name='passages')
    start_verse = models.ForeignKey(BibleVerse, on_delete=models.PROTECT, related_name='+')
    end_verse = models.ForeignKey(BibleVerse, on_delete=models.PROTECT, related_name='+')
    context_note = models.CharField(max_length=255, blank=True)
    ord = models.IntegerField(default=1)
    class Meta:
        ordering = ['ord']
        unique_together = ('sermon', 'ord')

class Attachment(models.Model):
    sermon = models.ForeignKey(Sermon, on_delete=models.CASCADE, related_name='attachments')
    rel_path = models.CharField(max_length=512)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=127)
    byte_size = models.BigIntegerField()
    uploaded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-uploaded_at']
