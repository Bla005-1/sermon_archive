from django.urls import path

from .api_views import SermonIllustrationDetailView, SermonIllustrationListView

urlpatterns = [
    path(
        "<int:sermon_id>/illustrations/",
        SermonIllustrationListView.as_view(),
        name="sermon-illustration-list",
    ),
    path(
        "<int:sermon_id>/illustrations/<int:illustration_id>/",
        SermonIllustrationDetailView.as_view(),
        name="sermon-illustration-detail",
    ),
]
