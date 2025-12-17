from django.urls import path

from .api_views import VerseCommentaryView, VerseCrossReferenceView, VersePassageView, VerseNoteDetailView, VerseNoteListCreateView

urlpatterns = [
    path("", VersePassageView.as_view(), name="verse-detail"),
    path("crossrefs/", VerseCrossReferenceView.as_view(), name="verse-crossrefs"),
    path("commentaries/", VerseCommentaryView.as_view(), name="verse-commentaries"),
    path("notes/", VerseNoteListCreateView.as_view(), name="bible-notes"),
    path("notes/<int:note_id>/", VerseNoteDetailView.as_view(), name="bible-note-detail"),
]