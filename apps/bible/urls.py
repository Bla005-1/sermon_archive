from django.urls import path

from .api_views import BibleLookupView, VerseNoteDetailView, VerseNoteListCreateView

urlpatterns = [
    path("lookup/", BibleLookupView.as_view(), name="bible-lookup"),
    path("notes/", VerseNoteListCreateView.as_view(), name="bible-notes"),
    path("notes/<int:note_id>/", VerseNoteDetailView.as_view(), name="bible-note-detail"),
]
