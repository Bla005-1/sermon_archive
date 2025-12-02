from django.contrib import admin

from apps.bible.models import BibleBook, BibleVerse
from .models import Attachment, Sermon, SermonPassage

admin.site.register([Sermon, BibleBook, BibleVerse, Attachment])
