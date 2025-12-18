from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Optional, cast

from django.core.exceptions import ValidationError
from django.db import DatabaseError

from ..models import Sermon

SERMON_FIELDS = ['preached_on', 'title', 'speaker_name', 'series_name', 'location_name', 'notes_md']


class SermonServiceError(Exception):
    """Raised when sermon persistence fails."""


def build_sermon_from_post(
    data: Mapping[str, Any],
    instance: Optional[Sermon] = None,
) -> Sermon:
    """Populate a ``Sermon`` instance for redisplay after a failed save."""

    sermon = instance or Sermon()
    for field in SERMON_FIELDS:
        if field == 'preached_on':
            raw_value = data.get(field)
            if raw_value:
                try:
                    parsed = Sermon._meta.get_field('preached_on').to_python(raw_value)
                    setattr(sermon, field, parsed)
                    sermon.preached_on_raw = ''
                    continue
                except ValidationError:
                    sermon.preached_on_raw = raw_value
                    setattr(sermon, field, None)
                    continue
            sermon.preached_on_raw = raw_value or ''
            setattr(sermon, field, None)
            continue
        setattr(sermon, field, data.get(field, getattr(sermon, field, '')))
    return sermon


def apply_sermon_data(sermon: Sermon, data: Mapping[str, object]) -> Sermon:
    data = data or {}
    for field in SERMON_FIELDS:
        setattr(sermon, field, data.get(field, getattr(sermon, field)))
    return sermon


def create_sermon(data: Mapping[str, Any]) -> Sermon:
    preached_on_value = cast(str | date | None, data.get('preached_on'))
    try:
        sermon = Sermon.objects.create(
            preached_on=preached_on_value or None,
            title=data.get('title', ''),
            speaker_name=data.get('speaker_name', ''),
            series_name=data.get('series_name', ''),
            location_name=data.get('location_name', ''),
            notes_md=data.get('notes_md', ''),
        )
    except (ValidationError, DatabaseError) as exc:
        raise SermonServiceError('Unable to save sermon.') from exc
    return sermon


def update_sermon(sermon: Sermon, data: Mapping[str, Any]) -> Sermon:
    apply_sermon_data(sermon, data)
    try:
        sermon.save()
    except (ValidationError, DatabaseError) as exc:
        raise SermonServiceError('Unable to update sermon.') from exc
    return sermon


def user_can_edit_sermons(user) -> bool:
    return user.is_authenticated and user.has_perm('sermons.change_sermon')
