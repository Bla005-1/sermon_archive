from django.urls import path

from .verse_api_views import VerseSermonsView

urlpatterns = [
    path("", VerseSermonsView.as_view(), name="verse-sermons"),
]
