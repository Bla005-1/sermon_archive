from datetime import date
from types import SimpleNamespace
from unittest import mock

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.sermons import verse_api_views


factory = APIRequestFactory()


def _auth_get(path: str):
    request = factory.get(path)
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return request


def test_verse_sermons_requires_reference_query():
    response = verse_api_views.VerseSermonsView.as_view()(_auth_get("/api/verses/sermons"))
    assert response.status_code == 400
    assert response.data["detail"] == "Provide a reference in the 'ref' query param."


def test_verse_sermons_rejects_parse_errors():
    with mock.patch.object(verse_api_views, "tolerant_parse_reference", side_effect=ValueError("bad ref")):
        response = verse_api_views.VerseSermonsView.as_view()(_auth_get("/api/verses/sermons?ref=bad"))

    assert response.status_code == 400
    assert response.data["detail"] == "bad ref"


def test_verse_sermons_sorts_exact_matches_first():
    start = SimpleNamespace(verse_id=50)
    end = SimpleNamespace(verse_id=50)

    sermon_exact = SimpleNamespace(pk=3, preached_on=date(2024, 1, 2), title="Exact", speaker_name="A", series_name="")
    sermon_overlap = SimpleNamespace(pk=2, preached_on=date(2023, 12, 31), title="Overlap", speaker_name="B", series_name="")

    passages = [
        SimpleNamespace(
            sermon=sermon_overlap,
            start_id=49,
            end_id=51,
            ref_text="John 3:15-17",
            context_note="range",
            start_verse=start,
            end_verse=end,
        ),
        SimpleNamespace(
            sermon=sermon_exact,
            start_id=50,
            end_id=50,
            ref_text="John 3:16",
            context_note="exact",
            start_verse=start,
            end_verse=end,
        ),
    ]

    manager = mock.Mock()
    manager.select_related.return_value = manager
    manager.annotate.return_value = manager
    manager.filter.return_value = passages

    request = _auth_get("/api/verses/sermons?ref=John+3%3A16")
    with mock.patch.object(verse_api_views.SermonPassage, "objects", manager), \
         mock.patch.object(verse_api_views, "tolerant_parse_reference", return_value=(start, end)), \
         mock.patch.object(verse_api_views, "format_ref", return_value="John 3:16"):
        response = verse_api_views.VerseSermonsView.as_view()(request)

    assert response.status_code == 200
    sermon_ids = [entry["sermon_id"] for entry in response.data["sermons"]]
    assert sermon_ids == [3, 2]
