from __future__ import annotations

import httpx

from app.config import settings
from tests.factories import seed_bible, seed_library, seed_sermons


def test_search_reference_intent_returns_canonical_url(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/search", params={"q": "John 3:16"})

    assert response.status_code == 200
    assert response.json() == {
        "intent": "reference",
        "reference": "John 3:16",
        "canonical_url": "/verse?ref=John+3%3A16",
    }


def test_search_proxies_unified_search_with_default_host_port(
    client, db_session, monkeypatch
):
    seed_bible(db_session)
    seen = {}

    def fake_get(url, *, params, timeout):
        seen["url"] = url
        seen["params"] = params
        seen["timeout"] = timeout
        return httpx.Response(
            200,
            json={
                "intent": "unified_search",
                "query": "creation",
                "total": 1,
                "results": [
                    {
                        "result_type": "library",
                        "resource_id": "library:100:unit:122",
                        "title": "Institutes",
                        "subtitle": "John Calvin",
                        "preview_text": "Creation text",
                        "href": "/library/100",
                        "score": 12.0,
                    }
                ],
            },
        )

    monkeypatch.setattr("app.services.search_service.httpx.get", fake_get)

    response = client.get(
        "/api/search",
        params=[
            ("q", "creation"),
            ("limit", "5"),
            ("offset", "2"),
            ("domains", "library"),
        ],
    )

    assert response.status_code == 200
    assert seen == {
        "url": "http://localhost:8051/api/search",
        "params": [
            ("q", "creation"),
            ("limit", 5),
            ("offset", 2),
            ("domains", "library"),
        ],
        "timeout": 3.0,
    }
    assert response.json() == {
        "intent": "search",
        "query": "creation",
        "total": 1,
        "results": [
            {
                "result_type": "library",
                "resource_id": "library:100:unit:122",
                "title": "Institutes",
                "subtitle": "John Calvin",
                "preview_text": "Creation text",
                "href": "/library/100",
                "score": 12.0,
            }
        ],
    }


def test_search_uses_configured_sermon_search_host_port(
    client, db_session, monkeypatch
):
    seed_bible(db_session)
    monkeypatch.setattr(settings, "sermon_search_host", "search.internal")
    monkeypatch.setattr(settings, "sermon_search_port", 9001)
    seen = {}

    def fake_get(url, *, params, timeout):
        seen["url"] = url
        return httpx.Response(
            200,
            json={
                "intent": "unified_search",
                "query": "grace",
                "total": 0,
                "results": [],
            },
        )

    monkeypatch.setattr("app.services.search_service.httpx.get", fake_get)

    response = client.get("/api/search", params={"q": "grace"})

    assert response.status_code == 200
    assert seen["url"] == "http://search.internal:9001/api/search"


def test_search_fallback_keyword_search_on_upstream_error(
    client, db_session, monkeypatch
):
    seed_bible(db_session)
    seed_sermons(db_session)
    seed_library(db_session)

    def fake_get(url, *, params, timeout):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.services.search_service.httpx.get", fake_get)

    response = client.get("/api/search", params={"q": "love judgment"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "search"
    assert body["query"] == "love judgment"
    assert body["total"] == 1
    assert body["results"][0]["result_type"] == "sermon"
    assert body["results"][0]["resource_id"] == "11"
    assert body["results"][0]["href"] == "/sermons/11"


def test_search_rejects_blank_query(client):
    response = client.get("/api/search", params={"q": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide a query in the 'q' query param."
