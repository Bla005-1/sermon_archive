from django.contrib import admin

from .models import Sermon, BibleBook, BibleVerse, SermonPassage, Attachment
admin.site.register([Sermon, BibleBook, BibleVerse, Attachment])
