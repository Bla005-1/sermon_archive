import os

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from apps.sermons.models import Attachment, Sermon
from apps.sermons.serializers import AttachmentSerializer
from apps.sermons.storage import AttachmentStorageError, resolve_attachment_path


class AttachmentDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]
    queryset = Attachment.objects.all()
    lookup_field = "pk"


class AttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        attachment = get_object_or_404(Attachment, pk=pk)
        sermon = get_object_or_404(Sermon, pk=attachment.sermon_id)
        try:
            abs_path = resolve_attachment_path(attachment.rel_path)
        except AttachmentStorageError as exc:
            raise Http404("Attachment not found.") from exc

        if not os.path.exists(abs_path):
            raise Http404("Attachment not found.")

        filename = attachment.original_filename or os.path.basename(abs_path)
        response = FileResponse(open(abs_path, "rb"), as_attachment=True, filename=filename)
        if attachment.mime_type:
            response["Content-Type"] = attachment.mime_type
        return response
