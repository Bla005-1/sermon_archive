from types import SimpleNamespace
from unittest import mock

import pytest
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.sermons import api_views


factory = APIRequestFactory()


def _authenticated_post(path: str, data: dict):
    request = factory.post(path, data=data, format="json")
    force_authenticate(request, user=SimpleNamespace(is_authenticated=True))
    return request


def test_passage_create_requires_reference():
    request = _authenticated_post("/sermons/1/passages/", {"context_note": "note"})
    response = api_views.SermonPassageListCreateView.as_view()(request, sermon_id=1)

    assert response.status_code == 400
    assert response.data["ref_text"] == ["Please include a reference like 'John 3:16'."]


def test_passage_create_returns_parser_errors():
    request = _authenticated_post("/sermons/1/passages/", {"ref_text": "bad", "context_note": ""})

    with mock.patch.object(api_views, "tolerant_parse_reference", side_effect=ValueError("bad ref")):
        response = api_views.SermonPassageListCreateView.as_view()(request, sermon_id=1)

    assert response.status_code == 400
    assert response.data["ref_text"] == ["bad ref"]
