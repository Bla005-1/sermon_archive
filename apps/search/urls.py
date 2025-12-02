from django.urls import path

from .api_views import ReferenceSearchView, SearchView

urlpatterns = [
    path("", SearchView.as_view(), name="search"),
    path("ref/", ReferenceSearchView.as_view(), name="search-ref"),
]
