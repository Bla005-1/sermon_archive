from django.urls import path

from .verse_api_views import (
    VerseCommentaryView,
    VerseCrossReferenceView,
    VersePassageView,
    VerseSermonsView,
)

urlpatterns = [
    path("", VersePassageView.as_view(), name="verse-detail"),
    path("sermons/", VerseSermonsView.as_view(), name="verse-sermons"),
    path("crossrefs/", VerseCrossReferenceView.as_view(), name="verse-crossrefs"),
    path("commentaries/", VerseCommentaryView.as_view(), name="verse-commentaries"),
]
