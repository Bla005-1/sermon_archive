from django.urls import path

from .api_views import AttachmentDetailView, AttachmentDownloadView

urlpatterns = [
    path("<int:pk>/", AttachmentDetailView.as_view(), name="attachment-detail-global"),
    path("<int:pk>/download/", AttachmentDownloadView.as_view(), name="attachment-download-global"),
]
