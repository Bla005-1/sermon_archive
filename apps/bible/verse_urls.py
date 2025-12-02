from django.urls import path

from .verse_api_views import VerseCommentaryView, VerseCrossReferenceView, VersePassageView

urlpatterns = [
    path("", VersePassageView.as_view(), name="verse-detail"),
    path("crossrefs/", VerseCrossReferenceView.as_view(), name="verse-crossrefs"),
    path("commentaries/", VerseCommentaryView.as_view(), name="verse-commentaries"),
]
