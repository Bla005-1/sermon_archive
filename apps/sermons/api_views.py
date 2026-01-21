import logging
import os

from django.contrib import messages
from django.db.models import QuerySet, Max
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
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

from apps.bible.models import BibleBook, BibleVerse
from apps.bible.utils.reference_parser import tolerant_parse_reference
from .models import Attachment, BibleWidgetVerse, Sermon, SermonPassage
from .serializers import AttachmentSerializer, SermonPassageSerializer, SermonSerializer
from .services.attachments import (
    AttachmentPersistenceError,
    AttachmentServiceError,
    delete_attachment,
    upload_attachment,
)
from .services import bible_widget as bible_widget_service
from .services import verse_tools as verse_tool_service
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


class SermonSuggestionView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        description="Return distinct speaker, series, and location names for sermons.",
    )
    def get(self, request, *args, **kwargs):
        speakers = (
            Sermon.objects
            .exclude(speaker_name__isnull=True)
            .exclude(speaker_name__exact="")
            .values("speaker_name")
            .annotate(latest=Max("preached_on"))
            .order_by("-latest")
            .values_list("speaker_name", flat=True)
        )

        series = (
            Sermon.objects
            .exclude(series_name__isnull=True)
            .exclude(series_name__exact="")
            .values("series_name")
            .annotate(latest=Max("preached_on"))
            .order_by("-latest")
            .values_list("series_name", flat=True)
        )

        locations = (
            Sermon.objects
            .exclude(location_name__isnull=True)
            .exclude(location_name__exact="")
            .values("location_name")
            .annotate(latest=Max("preached_on"))
            .order_by("-latest")
            .values_list("location_name", flat=True)
        )

        return Response(
            {
                "speakers": list(speakers),
                "series": list(series),
                "locations": list(locations),
            }
        )


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


def _load_passage_context(reference: str, translation: str):
    return verse_tool_service.load_passage_context(reference, forced_translation=translation)


def _build_related_sermons(reference_text: str, translation: str, start_verse_id: int, end_verse_id: int):
    return verse_tool_service.build_related_sermons(reference_text, translation, start_verse_id, end_verse_id)


def verse_tools(request):
    reference = (request.POST.get("reference") or "").strip()
    translation = (request.POST.get("selected_translation") or "").strip()
    form_action = request.POST.get("form_action") or ""

    context, error = _load_passage_context(reference, translation)
    if error:
        messages.error(request, error)
        return HttpResponse(status=400)

    context["related_sermons"] = _build_related_sermons(
        reference, translation, context.get("start_verse_id") or 0, context.get("end_verse_id") or 0
    )

    if form_action == "add_to_widget":
        if context.get("start_verse_id") != context.get("end_verse_id") or context.get("cross_references", {}).get(
            "is_passage"
        ):
            messages.error(request, "Please select a single verse before adding to the widget.")
            return HttpResponse(status=200)

        start_verse = get_object_or_404(BibleVerse, pk=context["start_verse_id"])
        end_verse = start_verse
        if context.get("end_verse_id"):
            end_verse = get_object_or_404(BibleVerse, pk=context["end_verse_id"])
        display_payload = context.get("translation_display_payload") or {}
        display_text = (display_payload.get(translation) or "").strip()

        created_entry, _ = BibleWidgetVerse.objects.update_or_create(
            start_verse=start_verse,
            end_verse=end_verse,
            defaults={
                "translation": translation,
                "ref": context.get("heading") or reference,
                "display_text": display_text,
            },
        )
        messages.success(request, "Added verse to the BibleWidget.")
        if len(display_text) > 155:
            messages.warning(request, "Display text is long; only the first 155 characters may be visible.")
        logger.debug("Added verse %s to widget as entry %s", reference, getattr(created_entry, "pk", None))
        return HttpResponse(status=200)

    return HttpResponse(status=200)


def bible_widget_list(request):
    action = request.POST.get("action")
    entry_id = request.POST.get("entry_id") or request.POST.get("id")

    if not entry_id:
        return redirect("/verses/widget")

    entry = get_object_or_404(BibleWidgetVerse, pk=entry_id)

    if action == "weight_up":
        bible_widget_service.adjust_weight(entry, 1)
        messages.success(request, f"Increased weight for {entry.ref}.")
    elif action == "weight_down":
        if entry.weight <= 1:
            messages.info(request, "Weight is already at the minimum value of 1.")
            return HttpResponseRedirect("/verses/widget")
        bible_widget_service.adjust_weight(entry, -1)
        messages.success(request, f"Decreased weight for {entry.ref}.")
    elif action == "update_text":
        display_text = (request.POST.get("display_text") or "").strip()
        entry.display_text = display_text
        entry.save(update_fields=["display_text"])
        messages.success(request, f"Updated display text for {entry.ref}.")
    elif action == "delete":
        bible_widget_service.delete_entry(entry)
        messages.success(request, f"Deleted {entry.ref} from the BibleWidget.")

    return HttpResponseRedirect("/verses/widget")


class AttachmentDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def handle_exception(self, exc):
        if isinstance(exc, Http404):
            raise exc
        return super().handle_exception(exc)

    def get(self, request, sermon_id: int, pk: int):
        sermon = get_object_or_404(Sermon, pk=sermon_id)
        attachment = get_object_or_404(Attachment, pk=pk, sermon_id=sermon_id)
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
