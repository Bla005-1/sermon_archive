from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bible.models import BibleVerse, VerseNote, VerseText
from apps.bible.utils.reference_parser import (
    build_commentary_context,
    determine_available_translations,
    format_ref,
    get_crossrefs_from,
    join_passage_text,
    select_default_translation,
    tolerant_parse_reference,
)


def _parse_reference(ref_text: str):
    try:
        start, end = tolerant_parse_reference(ref_text)
        return start, end, None
    except Exception as exc:  # pragma: no cover - parser raises helpful errors
        return None, None, str(exc)


def _load_passage_verses(start: BibleVerse, end: BibleVerse):
    return list(
        BibleVerse.objects.select_related("book")
        .filter(
            book=start.book,
            chapter=start.chapter,
            verse__gte=start.verse,
            verse__lte=end.verse,
        )
        .order_by("verse")
    )


def _select_translation(verses, translation_hint: str):
    verse_ids = [v.verse_id for v in verses]
    translation_map = {}
    for vt in VerseText.objects.filter(verse__in=verses):
        translation_map.setdefault(vt.translation, {})[vt.verse.verse_id] = vt.plain_text
    available = determine_available_translations(verse_ids, translation_map)
    selected = translation_hint if translation_hint in available else select_default_translation(available)
    if not selected and available:
        selected = available[0]
    return selected or "ESV", translation_map


def _preview_text_for_range(to_start_id: int, to_end_id: int) -> str:
    a, b = (min(to_start_id, to_end_id), max(to_start_id, to_end_id))
    rng = list(
        BibleVerse.objects.select_related("book")
        .filter(verse_id__gte=a, verse_id__lte=b)
        .order_by("verse_id")
    )
    if not rng:
        return ""
    rows = list(
        VerseText.objects.filter(verse__in=rng, translation="ESV").order_by("verse__verse")
    )
    if not rows:
        rows = list(
            VerseText.objects.filter(verse__in=rng).order_by("translation", "verse__verse")
        )
    lookup = {}
    for vt in rows:
        lookup.setdefault(vt.verse.verse_id, vt.plain_text)
    plain_text, _ = join_passage_text(rng, lookup)
    return plain_text


class VersePassageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference = (request.query_params.get("ref") or "").strip()
        translation_hint = (request.query_params.get("translation") or "ESV").strip()
        if not reference:
            return Response(
                {"detail": "Provide a reference in the 'ref' query param."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start, end, error = _parse_reference(reference)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        verses = _load_passage_verses(start, end)
        if not verses:
            return Response({"detail": "No verses found for the given reference."}, status=status.HTTP_404_NOT_FOUND)

        selected_translation, translation_map = _select_translation(verses, translation_hint)
        verse_lookup = translation_map.get(selected_translation, {})
        combined_text, _ = join_passage_text(verses, verse_lookup)

        notes_by_vid = {}
        for note in VerseNote.objects.filter(verse__in=verses).order_by("created_at"):
            if note.note_md:
                notes_by_vid.setdefault(note.verse_id, note.note_md)

        verse_payload = []
        for verse in verses:
            verse_payload.append(
                {
                    "verse_id": verse.verse_id,
                    "book": verse.book.name,
                    "chapter": verse.chapter,
                    "verse": verse.verse,
                    "text": verse_lookup.get(verse.verse_id, ""),
                    "notes": notes_by_vid.get(verse.verse_id),
                }
            )

        return Response(
            {
                "reference": format_ref(start, end),
                "translation": selected_translation,
                "text": combined_text,
                "verses": verse_payload,
            }
        )


class VerseCrossReferenceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference = (request.query_params.get("ref") or "").strip()
        if not reference:
            return Response(
                {"detail": "Provide a reference in the 'ref' query param."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start, end, error = _parse_reference(reference)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        verses = _load_passage_verses(start, end)
        crossrefs = get_crossrefs_from(verses)
        payload = []
        for verse in verses:
            items = []
            for cr in crossrefs.get(verse.verse_id, []):
                preview = _preview_text_for_range(cr["to_start_id"], cr["to_end_id"])
                items.append({**cr, "preview_text": preview})
            payload.append(
                {
                    "verse_id": verse.verse_id,
                    "book": verse.book.name,
                    "chapter": verse.chapter,
                    "verse": verse.verse,
                    "cross_references": items,
                }
            )

        return Response({"reference": format_ref(start, end), "verses": payload})


class VerseCommentaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reference = (request.query_params.get("ref") or "").strip()
        if not reference:
            return Response(
                {"detail": "Provide a reference in the 'ref' query param."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        start, end, error = _parse_reference(reference)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)

        verses = _load_passage_verses(start, end)
        commentary_context = build_commentary_context(verses)
        return Response(
            {
                "reference": format_ref(start, end),
                "count": commentary_context.get("count", 0),
                "items": commentary_context.get("items", []),
            }
        )
