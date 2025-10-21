from __future__ import annotations

from typing import Tuple

from django.db import DatabaseError

from ..models import BibleVerse, BibleWidgetVerse


class BibleWidgetError(Exception):
    pass


class BibleWidgetPersistenceError(BibleWidgetError):
    pass


def ensure_entry(
    start_verse: BibleVerse,
    end_verse: BibleVerse,
    translation: str,
    ref_text: str,
    display_text: str,
) -> Tuple[BibleWidgetVerse, bool]:
    defaults = {
        'translation': translation,
        'ref': ref_text,
        'display_text': display_text,
    }
    try:
        return BibleWidgetVerse.objects.update_or_create(start_verse=start_verse, end_verse=end_verse, defaults=defaults)
    except DatabaseError as exc:
        raise BibleWidgetPersistenceError('Unable to save BibleWidget verse.') from exc


def update_display_text(entry: BibleWidgetVerse, new_text: str) -> BibleWidgetVerse:
    entry.display_text = new_text
    try:
        entry.save(update_fields=['display_text'])
    except DatabaseError as exc:
        raise BibleWidgetPersistenceError('Unable to update BibleWidget display text.') from exc
    return entry


def adjust_weight(entry: BibleWidgetVerse, delta: int) -> BibleWidgetVerse:
    new_weight = max(1, min(entry.weight + delta, 65535))
    entry.weight = new_weight
    try:
        entry.save(update_fields=['weight'])
    except DatabaseError as exc:
        raise BibleWidgetPersistenceError('Unable to update BibleWidget weight.') from exc
    return entry


def delete_entry(entry: BibleWidgetVerse) -> None:
    try:
        entry.delete()
    except DatabaseError as exc:
        raise BibleWidgetPersistenceError('Unable to delete BibleWidget verse.') from exc
