from __future__ import annotations

import json

import httpx
import pytest

from sermon_archive.schemas import (
    Attachment,
    BibleWidget,
    LibraryItem,
    LibraryItemFile,
    LibraryItemUnit,
    LibraryUnitTypeEnum,
    PartialScriptureReference,
    Sermon,
    SermonSuggestionsResponse,
    ScriptureExtractionResponse,
    ScriptureReference,
    ScriptureReferenceCreate,
    ScriptureReferenceUpdate,
    TokenResponse,
    UserResponse,
    VerseCommentaryResponse,
    VerseLibraryItemReferenceResponse,
    VerseNote,
    VerseQueryResponse,
    VerseSermonResponse,
)
from sermon_archive.client import SermonArchiveClient, SermonArchiveClientError


SERMON = {"sermon_id": 10, "title": "Creation and Light"}
ATTACHMENT = {"attachment_id": 30, "sermon_id": 10}
LIBRARY_ITEM = {
    "library_item_id": 100,
    "title": "Institutes",
    "content_type": "book",
}
LIBRARY_FILE = {
    "library_item_file_id": 110,
    "library_item_id": 100,
    "original_filename": "institutes.pdf",
}
LIBRARY_UNIT = {
    "library_item_unit_id": 120,
    "library_item_id": 100,
    "unit_type": "chapter",
    "children": [],
}
VERSE_NOTE = {"note_id": 70, "verse_id": 1, "note_markdown": "Note"}
WIDGET = {
    "widget_passage_id": 50,
    "translation": "ESV",
    "reference_text": "Genesis 1:1",
    "display_text": "In the beginning",
}
VERSE_QUERY = {
    "intent": "reference",
    "query": "Genesis 1:1",
    "reference": "Genesis 1:1",
    "scope": "verse",
    "verses": [],
}
VERSE_SERMONS = {
    "reference": "Genesis 1:1",
    "sermons": [
        {
            "sermon_id": 10,
            "title": "Creation and Light",
            "preached_on": "2024-02-04",
            "speaker_name": "Ada",
            "series_name": "Beginnings",
            "reference": "Genesis 1:1",
            "context_note": "Opening text",
            "start_verse_id": 1,
            "end_verse_id": 1,
        }
    ],
}
VERSE_COMMENTARIES = {
    "reference": "Genesis 1:1",
    "count": 1,
    "items": [
        {
            "commentary_id": 90,
            "father_id": 20,
            "father_name": "Augustine",
            "display_name": "Augustine of Hippo",
            "append_to_author_name": "",
            "commentary_text": "In the beginning, God made all things.",
            "book_id": 1,
            "start_verse_id": 1,
            "end_verse_id": 1,
            "reference": "Genesis 1:1",
            "source_url": "https://example.test/commentary",
            "source_title": "On Genesis",
            "default_year": 400,
            "wiki_url": "https://example.test/augustine",
            "start": {
                "book": "Genesis",
                "chapter_number": 1,
                "verse_number": 1,
            },
            "end": {
                "book": "Genesis",
                "chapter_number": 1,
                "verse_number": 1,
            },
        }
    ],
}
VERSE_LIBRARY_ITEMS = {
    "reference": "Genesis 1:1",
    "library_items": [
        {
            "library_item_id": 100,
            "library_item_unit_id": 120,
            "title": "Institutes",
            "content_type": "book",
            "author_name": "John Calvin",
            "unit_title": "Opening paragraph",
            "unit_type": "paragraph",
            "unit_order": 3,
            "source_start_page_number": 7,
            "source_end_page_number": 8,
            "reference": "Genesis 1:1",
            "context_text": "Chapter 1 > Section 1",
            "start_verse_id": 1,
            "end_verse_id": 1,
        }
    ],
}
SCRIPTURE_REFERENCE = {
    "scripture_reference_id": 80,
    "source_type": "sermon",
    "source_id": 10,
    "start_verse_id": 1,
    "reference_text": "Genesis 1:1",
    "matched_text": "Gen 1:1",
}
SCRIPTURE_EXTRACTION = {"references": [SCRIPTURE_REFERENCE], "unresolved": []}
USER = {
    "id": 1,
    "username": "reader",
    "email": "reader@example.test",
    "first_name": "",
    "last_name": "",
    "is_active": True,
    "is_staff": False,
}
TOKEN = {
    "access_token": "issued-token",
    "token_type": "bearer",
    "expires_at": "2026-05-09T12:00:00",
}


def _json_response(data, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=data)


def test_client_imports_from_public_package():
    assert SermonArchiveClient.__name__ == "SermonArchiveClient"


def test_crud_get_methods_build_expected_requests_and_parse_models():
    responses = {
        ("GET", "/api/sermons", "q=creation"): [SERMON],
        ("GET", "/api/sermons/10", ""): SERMON,
        ("GET", "/api/sermons/suggestions", ""): {
            "speakers": ["Ada"],
            "series": ["Beginnings"],
            "locations": ["Main Hall"],
        },
        ("GET", "/api/sermons/10/attachments", ""): [ATTACHMENT],
        ("GET", "/api/attachments/30", ""): ATTACHMENT,
        ("GET", "/api/library/items", "q=institutes"): [LIBRARY_ITEM],
        ("GET", "/api/library/items/100", ""): LIBRARY_ITEM,
        ("GET", "/api/library/items/100/files", ""): [LIBRARY_FILE],
        ("GET", "/api/library/items/100/units", "root_unit_type=chapter"): [
            LIBRARY_UNIT
        ],
        ("GET", "/api/sermons/10/scripture-references", ""): [SCRIPTURE_REFERENCE],
        ("GET", "/api/scripture/references", "source_type=sermon&source_id=10"): [
            SCRIPTURE_REFERENCE
        ],
        ("GET", "/api/scripture/references/80", ""): SCRIPTURE_REFERENCE,
        (
            "GET",
            "/api/library/items/100/units/120/scripture-references",
            "",
        ): [SCRIPTURE_REFERENCE | {"source_type": "library_item_unit", "source_id": 120}],
        ("GET", "/api/verses/sermons", "ref=Genesis+1%3A1"): VERSE_SERMONS,
        (
            "GET",
            "/api/verses/commentaries",
            "ref=Genesis+1%3A1",
        ): VERSE_COMMENTARIES,
        (
            "GET",
            "/api/verses/library-items",
            "ref=Genesis+1%3A1",
        ): VERSE_LIBRARY_ITEMS,
        ("GET", "/api/verses/notes", "verse_id=1"): [VERSE_NOTE],
        ("GET", "/api/verses/notes/70", ""): VERSE_NOTE,
        ("GET", "/api/widget", ""): [WIDGET],
        ("GET", "/api/widget/50", ""): WIDGET,
    }
    seen: list[tuple[str, str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        key = (request.method, request.url.path, request.url.query.decode())
        seen.append(key)
        return _json_response(responses[key])

    client = SermonArchiveClient(
        "http://testserver",
        bearer_token="token-123",
        transport=httpx.MockTransport(handler),
    )

    assert isinstance(client.list_sermons(q="creation")[0], Sermon)
    assert isinstance(client.get_sermon(10), Sermon)
    assert isinstance(client.get_sermon_suggestions(), SermonSuggestionsResponse)
    assert isinstance(client.list_sermon_attachments(10)[0], Attachment)
    assert isinstance(client.get_attachment(30), Attachment)
    assert isinstance(client.list_library_items(q="institutes")[0], LibraryItem)
    assert isinstance(client.get_library_item(100), LibraryItem)
    assert isinstance(client.list_library_item_files(100)[0], LibraryItemFile)
    assert isinstance(
        client.list_library_item_units(100, LibraryUnitTypeEnum.chapter)[0],
        LibraryItemUnit,
    )
    assert isinstance(client.list_sermon_scripture_references(10)[0], ScriptureReference)
    assert isinstance(
        client.list_scripture_references("sermon", 10)[0],
        ScriptureReference,
    )
    assert isinstance(client.get_scripture_reference(80), ScriptureReference)
    assert isinstance(
        client.list_library_item_unit_scripture_references(100, 120)[0],
        ScriptureReference,
    )
    assert isinstance(
        client.get_sermons_for_reference("Genesis 1:1"),
        VerseSermonResponse,
    )
    assert isinstance(
        client.get_commentaries_for_reference("Genesis 1:1"),
        VerseCommentaryResponse,
    )
    assert isinstance(
        client.get_library_items_for_reference("Genesis 1:1"),
        VerseLibraryItemReferenceResponse,
    )
    assert isinstance(client.list_verse_notes(verse_id=1)[0], VerseNote)
    assert isinstance(client.get_verse_note(70), VerseNote)
    assert isinstance(client.list_widgets()[0], BibleWidget)
    assert isinstance(client.get_widget(50), BibleWidget)

    assert seen == list(responses)


def test_library_file_helpers_upload_download_and_preview():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/library/items/100/files":
            assert request.method == "POST"
            assert b'name="file"; filename="outline.docx"' in request.content
            return _json_response(LIBRARY_FILE, status_code=201)
        if request.url.path.endswith("/download"):
            return httpx.Response(200, content=b"download bytes")
        if request.url.path.endswith("/preview"):
            return httpx.Response(200, content=b"preview bytes")
        raise AssertionError(f"Unexpected path {request.url.path}")

    client = SermonArchiveClient(
        "http://testserver",
        bearer_token="token-123",
        transport=httpx.MockTransport(handler),
    )

    uploaded = client.upload_library_item_file(
        100,
        "outline.docx",
        b"docx bytes",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    downloaded = client.download_library_item_file(100, 110)
    previewed = client.preview_library_item_file(100, 110)

    assert isinstance(uploaded, LibraryItemFile)
    assert downloaded == b"download bytes"
    assert previewed == b"preview bytes"
    assert requests[0].headers["Authorization"] == "Bearer token-123"


def test_scripture_extraction_client_helpers():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json_response(SCRIPTURE_EXTRACTION)

    client = SermonArchiveClient(
        "http://testserver",
        bearer_token="token-123",
        transport=httpx.MockTransport(handler),
    )

    preview = client.extract_scripture_references("See Gen 1:1")
    library = client.extract_library_item_unit_scripture_references(100, 120)
    sermon = client.extract_sermon_scripture_references(10)

    assert isinstance(preview, ScriptureExtractionResponse)
    assert isinstance(library, ScriptureExtractionResponse)
    assert isinstance(sermon, ScriptureExtractionResponse)
    assert [request.url.path for request in requests] == [
        "/api/scripture/extract",
        "/api/library/items/100/units/120/scripture-references/extract",
        "/api/sermons/10/scripture-references/extract",
    ]


def test_scripture_reference_crud_client_helpers():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.method == "DELETE":
            return httpx.Response(204)
        return _json_response(SCRIPTURE_REFERENCE)

    client = SermonArchiveClient(
        "http://testserver",
        bearer_token="token-123",
        transport=httpx.MockTransport(handler),
    )

    created = client.create_scripture_reference(
        ScriptureReferenceCreate(
            source_type="sermon",
            source_id=10,
            reference_text="Gen 1:1",
        )
    )
    updated = client.update_scripture_reference(
        80,
        ScriptureReferenceUpdate(
            source_type="sermon",
            source_id=10,
            reference_text="Gen 1:1",
        ),
    )
    patched = client.patch_scripture_reference(
        80,
        PartialScriptureReference(context_text="patched"),
    )
    deleted = client.delete_scripture_reference(80)

    assert isinstance(created, ScriptureReference)
    assert isinstance(updated, ScriptureReference)
    assert isinstance(patched, ScriptureReference)
    assert deleted is None
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/api/scripture/references"),
        ("PUT", "/api/scripture/references/80"),
        ("PATCH", "/api/scripture/references/80"),
        ("DELETE", "/api/scripture/references/80"),
    ]


def test_bearer_auth_header_is_sent_and_can_be_updated():
    authorization_headers: list[str | None] = []

    def handler(request: httpx.Request) -> httpx.Response:
        authorization_headers.append(request.headers.get("Authorization"))
        return _json_response(USER)

    client = SermonArchiveClient(
        "http://testserver",
        bearer_token="first-token",
        transport=httpx.MockTransport(handler),
    )

    assert isinstance(client.me(), UserResponse)
    client.set_bearer_token("second-token")
    client.me()
    client.set_bearer_token(None)
    client.me()

    assert authorization_headers == [
        "Bearer first-token",
        "Bearer second-token",
        None,
    ]


def test_get_verse_uses_direct_reference_endpoint_and_parses_response():
    seen_request: httpx.Request | None = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return _json_response(VERSE_QUERY)

    client = SermonArchiveClient(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    response = client.get_verse("Genesis 1:1", translation="KJV")

    assert isinstance(response, VerseQueryResponse)
    assert response.reference == "Genesis 1:1"
    assert seen_request is not None
    assert seen_request.method == "GET"
    assert seen_request.url.path == "/api/verses/reference"
    assert seen_request.url.params["ref"] == "Genesis 1:1"
    assert seen_request.url.params["translation"] == "KJV"


def test_auth_methods_send_payloads_cookies_csrf_and_parse_responses():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/auth/csrf":
            return httpx.Response(
                200,
                json={"detail": "CSRF cookie set."},
                headers={"Set-Cookie": "csrftoken=csrf-123; Path=/"},
            )
        if request.url.path == "/api/auth/login":
            assert json.loads(request.content) == {
                "username": "reader",
                "password": "secret",
            }
            return _json_response(USER)
        if request.url.path == "/api/auth/token":
            assert json.loads(request.content) == {
                "username": "reader",
                "password": "secret",
                "token_name": "ci",
            }
            return _json_response(TOKEN)
        if request.url.path == "/api/auth/token/revoke":
            return _json_response({"detail": "Token revoked."})
        if request.url.path == "/api/auth/refresh":
            return _json_response(USER)
        if request.url.path == "/api/auth/logout":
            return httpx.Response(200)
        raise AssertionError(f"Unexpected path {request.url.path}")

    client = SermonArchiveClient(
        "http://testserver",
        bearer_token="stored-token",
        transport=httpx.MockTransport(handler),
    )

    client.csrf()
    assert isinstance(client.login("reader", "secret"), UserResponse)
    assert isinstance(client.issue_token("reader", "secret", "ci"), TokenResponse)
    assert client.revoke_token("override-token").detail == "Token revoked."
    assert isinstance(client.refresh(), UserResponse)
    client.logout()

    by_path = {request.url.path: request for request in requests}
    assert by_path["/api/auth/login"].headers["X-CSRF-Token"] == "csrf-123"
    assert by_path["/api/auth/token"].headers["X-CSRF-Token"] == "csrf-123"
    assert by_path["/api/auth/refresh"].headers["X-CSRF-Token"] == "csrf-123"
    assert by_path["/api/auth/logout"].headers["X-CSRF-Token"] == "csrf-123"
    assert (
        by_path["/api/auth/token/revoke"].headers["Authorization"]
        == "Bearer override-token"
    )


def test_error_includes_status_detail_and_body_for_json_response():
    def handler(_request: httpx.Request) -> httpx.Response:
        return _json_response({"detail": "Authentication required."}, status_code=401)

    client = SermonArchiveClient(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SermonArchiveClientError) as exc_info:
        client.me()

    error = exc_info.value
    assert error.status_code == 401
    assert error.detail == "Authentication required."
    assert error.body == {"detail": "Authentication required."}


def test_error_uses_text_body_for_non_json_response():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="Internal server error")

    client = SermonArchiveClient(
        "http://testserver",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(SermonArchiveClientError) as exc_info:
        client.list_widgets()

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Internal server error"
