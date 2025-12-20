from __future__ import annotations

from typing import Iterable, Mapping, Sequence, Tuple

from apps.bible.models import BibleVerse
from apps.sermons.services import verse_tools


def _determine_available_translations(verse_ids: Iterable[int], translation_map: Mapping[str, Mapping[int, str]]) -> list[str]:
    available: list[str] = []
    verse_id_set = set(verse_ids)
    for translation, text_map in translation_map.items():
        if verse_id_set.issubset(text_map.keys()):
            available.append(translation)
    return available


def _select_default_translation(available: Sequence[str]) -> str | None:
    for preferred in verse_tools.PREFERRED_TRANSLATIONS:
        if preferred in available:
            return preferred
    return available[0] if available else None


def _join_passage_text(
    verses: Sequence[object],
    verse_lookup: Mapping[int, str],
) -> Tuple[str, str]:
    plain_parts: list[str] = []
    display_parts: list[str] = []

    for verse in verses:
        verse_id = getattr(verse, "verse_id")
        verse_number = getattr(verse, "verse")
        text = (verse_lookup.get(verse_id) or "").strip()
        if not text:
            continue
        plain_parts.append(text)
        display_parts.append(f'<span class="sup">{verse_number}</span> {text}')

    plain = " ".join(plain_parts)
    display = " ".join(display_parts)
    return plain, display


def _strip_superscripts(text: str) -> str:
    cleaned = verse_tools.strip_superscripts(text)
    return cleaned


_serialize_related_passages = verse_tools._serialize_related_passages  # type: ignore[attr-defined]


def _resolve_reference_from_ids(verse_id_param: str, start_param: str, end_param: str) -> str:
    verse_id_param = (verse_id_param or "").strip()
    start_param = (start_param or "").strip()
    end_param = (end_param or "").strip()

    if verse_id_param:
        try:
            verse_id = int(verse_id_param)
            verse = BibleVerse.objects.select_related("book").get(pk=verse_id)
            return f"{verse.book.name} {verse.chapter}:{verse.verse}"
        except (ValueError, BibleVerse.DoesNotExist):
            return ""

    if start_param:
        try:
            start_id = int(start_param)
        except ValueError:
            return ""
        try:
            start_verse = BibleVerse.objects.select_related("book").get(pk=start_id)
        except BibleVerse.DoesNotExist:
            return ""
        end_verse = start_verse
        if end_param:
            try:
                end_id = int(end_param)
                end_verse = BibleVerse.objects.select_related("book").get(pk=end_id)
            except (ValueError, BibleVerse.DoesNotExist):
                end_verse = start_verse
        if end_verse.verse_id < start_verse.verse_id:
            start_verse, end_verse = end_verse, start_verse
        book_name = getattr(start_verse.book, "name", "")
        if getattr(start_verse, "book", None) and getattr(end_verse, "book", None):
            if getattr(start_verse.book, "name", "") == getattr(end_verse.book, "name", ""):
                if start_verse.chapter == end_verse.chapter:
                    return f"{book_name} {start_verse.chapter}:{start_verse.verse}–{end_verse.verse}"
                return (
                    f"{book_name} {start_verse.chapter}:{start_verse.verse}"
                    f"–{end_verse.chapter}:{end_verse.verse}"
                )
            return (
                f"{getattr(start_verse.book, 'name', '')} {start_verse.chapter}:{start_verse.verse}"
                f"–{getattr(end_verse.book, 'name', '')} {end_verse.chapter}:{end_verse.verse}"
            )
        return ""

    return ""


__all__ = [
    "_determine_available_translations",
    "_join_passage_text",
    "_resolve_reference_from_ids",
    "_select_default_translation",
    "_serialize_related_passages",
    "_strip_superscripts",
]
