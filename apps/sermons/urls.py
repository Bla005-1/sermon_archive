from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    AttachmentDetailView,
    AttachmentDownloadView,
    AttachmentListCreateView,
    PassageDetailView,
    SermonPassageDetailView,
    SermonPassageListCreateView,
    SermonViewSet,
)

router = DefaultRouter()
router.register("", SermonViewSet, basename="sermon")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "<int:sermon_id>/passages/",
        SermonPassageListCreateView.as_view(),
        name="sermon-passage-list",
    ),
    path(
        "<int:sermon_id>/passages/<int:pk>/",
        SermonPassageDetailView.as_view(),
        name="sermon-passage-detail",
    ),
    path("passages/<int:pk>/", PassageDetailView.as_view(), name="passage-detail"),
    path(
        "<int:sermon_id>/attachments/",
        AttachmentListCreateView.as_view(),
        name="attachment-list",
    ),
    path(
        "<int:sermon_id>/attachments/<int:pk>/",
        AttachmentDetailView.as_view(),
        name="attachment-detail",
    ),
    path(
        "<int:sermon_id>/attachments/<int:pk>/download/",
        AttachmentDownloadView.as_view(),
        name="attachment-download",
    ),
]
