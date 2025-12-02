from __future__ import annotations

from typing import Tuple

from django.db import DatabaseError
from django.db.models import Max

from apps.bible.utils.reference_parser import tolerant_parse_reference
from ..models import Sermon, SermonPassage


class PassageServiceError(Exception):
    """Base error for passage operations."""


class PassageParseError(PassageServiceError):
    pass


class PassagePersistenceError(PassageServiceError):
    pass


def parse_reference(ref_text: str) -> Tuple:
    try:
        return tolerant_parse_reference(ref_text)
    except ValueError as exc:
        raise PassageParseError(str(exc)) from exc


def add_passage(sermon: Sermon, ref_text: str, context_note: str = '') -> SermonPassage:
    start_v, end_v = parse_reference(ref_text)
    next_ord = (sermon.passages.aggregate(m=Max('ord'))['m'] or 0) + 1
    try:
        return SermonPassage.objects.create(
            sermon=sermon,
            start_verse=start_v,
            end_verse=end_v,
            context_note=context_note,
            ord=next_ord,
            ref_text=ref_text,
        )
    except DatabaseError as exc:
        raise PassagePersistenceError('Unable to save passage.') from exc


def delete_passage(sermon: Sermon, ord: int) -> int:
    deleted, _ = SermonPassage.objects.filter(sermon=sermon, ord=ord).delete()
    _normalize_ordering(sermon)
    return deleted


def update_passage_note(passage: SermonPassage, context_note: str) -> SermonPassage:
    passage.context_note = context_note
    try:
        passage.save(update_fields=['context_note'])
    except DatabaseError as exc:
        raise PassagePersistenceError('Unable to update passage note.') from exc
    return passage


def _normalize_ordering(sermon: Sermon) -> None:
    for idx, passage in enumerate(sermon.passages.order_by('ord'), start=1):
        if passage.ord != idx:
            passage.ord = idx
            passage.save(update_fields=['ord'])
