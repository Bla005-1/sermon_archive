from types import SimpleNamespace
from unittest import mock

from rest_framework.test import APIRequestFactory, force_authenticate

from apps.bible import api_views


factory = APIRequestFactory()


def _auth_get(path: str):
    request = factory.get(path)
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return request


def test_verse_passage_returns_intent_for_text_query():
    request = _auth_get("/api/verses?query=for+God+so+loved")
    with mock.patch.object(api_views, "_parse_reference", side_effect=ValueError("no ref")), \
         mock.patch.object(api_views, "_load_passage_verses") as load_mock:
        response = api_views.VersePassageView.as_view()(request)

    load_mock.assert_not_called()
    assert response.status_code == 200
    assert response.data == {"type": "text", "query": "for God so loved"}


def test_verse_passage_includes_type_when_reference_found():
    book = SimpleNamespace(name="John")
    verse = SimpleNamespace(book=book, chapter=3, verse=16, verse_id=31601)
    translation_map = {"ESV": {verse.verse_id: "For God so loved the world"}}
    marked_translation_map = {"ESV": {verse.verse_id: "<sup>16</sup> For God so loved the world"}}
    notes_qs = mock.Mock()
    notes_qs.order_by.return_value = []

    request = _auth_get("/api/verses?query=John+3%3A16&translation=ESV")
    with mock.patch.object(api_views, "_parse_reference", return_value=(verse, verse)), \
         mock.patch.object(api_views, "_load_passage_verses", return_value=[verse]), \
         mock.patch.object(api_views, "_select_translation", return_value=("ESV", translation_map, marked_translation_map, ["ESV"])), \
         mock.patch.object(api_views, "join_passage_text", return_value=("plain", "marked")), \
         mock.patch.object(api_views.VerseNote.objects, "filter", return_value=notes_qs):
        response = api_views.VersePassageView.as_view()(request)

    assert response.status_code == 200
    assert response.data["type"] == "reference"
    assert response.data["reference"] == "John 3:16"
    assert response.data["translation"] == "ESV"
    assert response.data["verses"][0]["text"] == "For God so loved the world"
    notes_qs.order_by.assert_called_once_with("created_at")
