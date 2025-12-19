import logging
import os

from django.db.models import QuerySet
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveDestroyAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from apps.bible.utils.reference_parser import tolerant_parse_reference
from .models import Attachment, Sermon, SermonPassage
from .serializers import AttachmentSerializer, SermonPassageSerializer, SermonSerializer
from .services.attachments import (
    AttachmentPersistenceError,
    AttachmentServiceError,
    delete_attachment,
    upload_attachment,
)
from .storage import AttachmentStorageError, resolve_attachment_path

logger = logging.getLogger(__name__)


@extend_schema_view(
    list=extend_schema(
        description="List sermons, optionally filtered by a title search term.",
        parameters=[
            OpenApiParameter(
                name="q",
                type=str,
                location=OpenApiParameter.QUERY,
                description="Full or partial sermon title to filter the list.",
            )
        ],
    )
)
class SermonViewSet(viewsets.ModelViewSet):
    serializer_class = SermonSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "sermon_id"
    queryset = Sermon.objects.all()

    def get_queryset(self) -> QuerySet[Sermon]:
        sermons: QuerySet[Sermon] = self.queryset.prefetch_related(
            "attachments",
            "passages__start_verse__book",
            "passages__end_verse__book",
        ).order_by("-preached_on", "-sermon_id")
        query = self.request.query_params.get("q", "").strip()
        if query:
            sermons = sermons.filter(title__icontains=query)
            logger.debug("Filtering sermons with query '%s'", query)
        return sermons


class SermonPassageListCreateView(ListCreateAPIView):
    serializer_class = SermonPassageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[SermonPassage]:
        return (
            SermonPassage.objects.filter(sermon_id=self.kwargs["sermon_id"])
            .select_related("sermon", "start_verse__book", "end_verse__book")
            .order_by("ord", "id")
        )

    def create(self, request, *args, **kwargs):
        ref_text = (request.data.get("ref_text") or "").strip()
        if not ref_text:
            raise ValidationError({"ref_text": ["Please include a reference like 'John 3:16'."]})
        try:
            start_verse, end_verse = tolerant_parse_reference(ref_text)
        except ValueError as exc:
            raise ValidationError({"ref_text": [str(exc)]}) from exc

        data = request.data.copy()
        data["ref_text"] = ref_text
        data["start_verse_id"] = start_verse.pk
        if end_verse and end_verse.pk != start_verse.pk:
            data["end_verse_id"] = end_verse.pk
        else:
            data.pop("end_verse_id", None)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        sermon = get_object_or_404(Sermon, pk=self.kwargs["sermon_id"])
        validated = serializer.validated_data
        passage = SermonPassage.objects.add_ordered(
            sermon=sermon,
            start_verse=start_verse,
            end_verse=end_verse if end_verse.pk != start_verse.pk else None,
            ref_text=ref_text,
            context_note=validated.get("context_note"),
        )
        output = SermonPassageSerializer(passage)
        headers = self.get_success_headers(output.data)
        return Response(output.data, status=status.HTTP_201_CREATED, headers=headers)


class SermonPassageDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = SermonPassageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[SermonPassage]:
        return (
            SermonPassage.objects.filter(sermon_id=self.kwargs["sermon_id"])
            .select_related("sermon", "start_verse__book", "end_verse__book")
            .order_by("ord", "id")
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        logger.info("Updated passage %s for sermon %s", instance.pk, instance.sermon_id)
        return instance


class PassageDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = SermonPassageSerializer
    permission_classes = [IsAuthenticated]
    queryset = SermonPassage.objects.select_related(
        "sermon", "start_verse__book", "end_verse__book"
    ).all()


class AttachmentListCreateView(ListCreateAPIView):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self) -> QuerySet[Attachment]:
        return Attachment.objects.filter(sermon_id=self.kwargs["sermon_id"]).order_by(
            "-created_at"
        )

    def create(self, request, *args, **kwargs):
        sermon = get_object_or_404(Sermon, pk=self.kwargs["sermon_id"])
        upload = request.FILES.get("file") or request.data.get("file")
        if not upload:
            raise ValidationError({"file": ["Please include a file upload."]})
        try:
            attachment, meta = upload_attachment(sermon, upload)
        except AttachmentServiceError as exc:
            logger.exception("Attachment upload failed for sermon %s", sermon.pk)
            raise ValidationError({"file": [str(exc)]}) from exc
        except AttachmentPersistenceError as exc:
            logger.exception("Attachment metadata save failed for sermon %s", sermon.pk)
            raise ValidationError({"detail": ["Unable to save attachment metadata."]}) from exc
        logger.info(
            "Uploaded attachment %s (%s bytes) to sermon %s",
            attachment.pk,
            meta.get("byte_size"),
            sermon.pk,
        )
        serializer = self.get_serializer(attachment)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class AttachmentDetailView(RetrieveDestroyAPIView):
    serializer_class = AttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet[Attachment]:
        return Attachment.objects.filter(sermon_id=self.kwargs["sermon_id"])

    def perform_destroy(self, instance):
        delete_attachment(instance.sermon, instance.pk)
        logger.info("Deleted attachment %s from sermon %s", instance.pk, instance.sermon_id)


class AttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, sermon_id: int, pk: int):
        sermon = get_object_or_404(Sermon, pk=sermon_id)
        attachment = get_object_or_404(sermon.attachments, pk=pk)
        try:
            abs_path = resolve_attachment_path(attachment.rel_path)
        except AttachmentStorageError as exc:
            logger.exception(
                "Attachment %s for sermon %s resolved outside storage root", pk, sermon_id
            )
            raise Http404("Attachment not found.") from exc

        if not os.path.exists(abs_path):
            logger.warning(
                "Attachment %s for sermon %s missing from filesystem path %s",
                pk,
                sermon_id,
                abs_path,
            )
            raise Http404("Attachment not found.")

        filename = attachment.original_filename or os.path.basename(abs_path)
        response = FileResponse(open(abs_path, "rb"), as_attachment=True, filename=filename)
        if attachment.mime_type:
            response["Content-Type"] = attachment.mime_type
        return response
