from __future__ import annotations

import httpx

from app.config import settings
from tests.factories import seed_bible


def _group(result_type: str, source_id: str, href: str, *, match_id: str | None = None):
    level = "library_section" if result_type == "library" else result_type
    return {
        "result_type": result_type,
        "group_level": level,
        "group_id": f"{source_id}:group",
        "title": "Result title",
        "source_id": source_id,
        "source_title": "Source title",
        "source_subtitle": "Source subtitle",
        "href": href,
        "score": 12.0,
        "match_count": 1,
        "matches": [
            {
                "resource_id": match_id or source_id,
                "title": "Matching passage",
                "subtitle": "KJV" if result_type == "verse" else None,
                "preview_text": "Matching text",
                "href": href,
                "score": 11.0,
            }
        ],
    }


def test_search_reference_intent_returns_canonical_url(client, db_session):
    seed_bible(db_session)
    response = client.get("/api/search", params={"q": "John 3:16"})
    assert response.status_code == 200
    assert response.json() == {
        "intent": "reference",
        "reference": "John 3:16",
        "canonical_url": "/verse?ref=John+3%3A16",
    }


def test_search_proxies_grouped_results_and_domain_filters(client, db_session, monkeypatch):
    seed_bible(db_session)
    seen = {}

    def fake_post(url, *, json, timeout):
        seen.update(url=url, json=json, timeout=timeout)
        return httpx.Response(
            200,
            json={
                "intent": "unified_search",
                "query": "creation",
                "total": 1,
                "results": [
                    _group(
                        "library",
                        "library:100",
                        "/library/items/100",
                        match_id="library:100:unit:122",
                    )
                ],
            },
        )

    monkeypatch.setattr("app.services.search_index_client.httpx.post", fake_post)
    response = client.get(
        "/api/search",
        params=[("q", "creation"), ("limit", "5"), ("offset", "2"), ("domains", "library")],
    )

    assert response.status_code == 200
    assert seen == {
        "url": f"http://{settings.sermon_search_host}:{settings.sermon_search_port}/api/search/query",
        "json": {
            "query": "creation",
            "match_mode": "auto",
            "limit": 5,
            "offset": 2,
            "filters": {"domains": ["library"]},
        },
        "timeout": max(settings.sermon_search_timeout_seconds, 7.0),
    }
    result = response.json()["results"][0]
    assert result["href"] == "/library-item?id=100#library-unit-122"
    assert result["matches"][0]["href"] == "/library-item?id=100#library-unit-122"


def test_search_uses_configured_sermon_search_host_port(client, db_session, monkeypatch):
    seed_bible(db_session)
    monkeypatch.setattr(settings, "sermon_search_host", "search.internal")
    monkeypatch.setattr(settings, "sermon_search_port", 9001)
    seen = {}

    def fake_post(url, *, json, timeout):
        seen.update(url=url, json=json)
        return httpx.Response(200, json={"intent": "unified_search", "query": "grace", "total": 0, "results": []})

    monkeypatch.setattr("app.services.search_index_client.httpx.post", fake_post)
    response = client.get("/api/search", params={"q": "grace"})
    assert response.status_code == 200
    assert seen["url"] == "http://search.internal:9001/api/search/query"


def test_search_returns_503_when_sermon_search_is_unavailable(client, db_session, monkeypatch):
    seed_bible(db_session)

    def fake_post(url, *, json, timeout):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("app.services.search_index_client.httpx.post", fake_post)
    response = client.get("/api/search", params={"q": "love judgment"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Search is temporarily unavailable. Please try again."


def test_search_returns_502_for_invalid_grouped_response(client, db_session, monkeypatch):
    seed_bible(db_session)

    def fake_post(url, *, json, timeout):
        return httpx.Response(200, json={"intent": "unified_search", "query": "grace", "total": 1, "results": [{"title": "Incomplete"}]})

    monkeypatch.setattr("app.services.search_index_client.httpx.post", fake_post)
    response = client.get("/api/search", params={"q": "grace"})
    assert response.status_code == 502
    assert response.json()["detail"] == "Search returned an invalid response. Please try again."


def test_search_accepts_all_collapsed_verse_translations(client, db_session, monkeypatch):
    seed_bible(db_session)
    group = _group("verse", "verse:john:3:16", "/verse/John%203%3A16")
    group["match_count"] = 4
    group["matches"] = [
        {
            "resource_id": f"verse:{translation}:26264",
            "title": "John 3:16",
            "subtitle": translation,
            "preview_text": f"{translation} verse text",
            "href": "/verse/John%203%3A16",
            "score": 10.0 - index,
        }
        for index, translation in enumerate(["ESV", "KJV", "NASB", "NIV"])
    ]

    def fake_post(url, *, json, timeout):
        return httpx.Response(
            200,
            json={"intent": "unified_search", "query": "love", "total": 1, "results": [group]},
        )

    monkeypatch.setattr("app.services.search_index_client.httpx.post", fake_post)
    response = client.get("/api/search", params={"q": "love"})
    assert response.status_code == 200
    matches = response.json()["results"][0]["matches"]
    assert [match["subtitle"] for match in matches] == ["ESV", "KJV", "NASB", "NIV"]


def test_search_normalizes_group_and_match_links(client, db_session, monkeypatch):
    seed_bible(db_session)
    groups = [
        _group("sermon", "sermon:10", "/sermons/10", match_id="sermon:10:unit:2"),
        _group("library", "library:100", "/library/100", match_id="library:100:unit:122"),
        _group("verse", "verse:john:3:16", "/verse/John%203%3A16", match_id="verse:ESV:26264:unit:1"),
    ]

    def fake_post(url, *, json, timeout):
        return httpx.Response(200, json={"intent": "unified_search", "query": "john", "total": 3, "results": groups})

    monkeypatch.setattr("app.services.search_index_client.httpx.post", fake_post)
    response = client.get("/api/search", params={"q": "john"})
    assert response.status_code == 200
    body = response.json()["results"]
    assert [result["href"] for result in body] == [
        "/sermon?id=10",
        "/library-item?id=100#library-unit-122",
        "/verse?ref=John+3%3A16",
    ]
    assert body[1]["matches"][0]["href"] == "/library-item?id=100#library-unit-122"


def test_search_rejects_blank_query(client):
    response = client.get("/api/search", params={"q": "   "})
    assert response.status_code == 400
    assert response.json()["detail"] == "Provide a query in the 'q' query param."
