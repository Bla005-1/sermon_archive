from django.urls import path

from .api_views import ReferenceSearchView, SermonSearchView, VerseSearchView

urlpatterns = [
    path("", VerseSearchView.as_view(), name="search"),
    path("sermons/", SermonSearchView.as_view(), name="search-sermons"),
    path("ref/", ReferenceSearchView.as_view(), name="search-ref"),
]
