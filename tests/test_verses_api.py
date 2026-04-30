from __future__ import annotations

from sqlalchemy import select

from app.db.models import VerseNotes
from tests.factories import (
    seed_bible,
    seed_commentary_and_crossrefs,
    seed_sermons,
    seed_verse_notes,
)


def test_verses_lookup_reference_prefers_requested_translation(client, db_session):
    seed_bible(db_session)

    response = client.get(
        "/api/verses",
        params={"q": "Genesis 1:1", "translation": "kjv"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "reference"
    assert body["reference"] == "Genesis 1:1"
    assert body["scope"] == "verse"
    assert body["verses"][0]["translation"] == "KJV"
    assert body["verses"][0]["available_translations"] == ["ESV", "KJV"]
    assert body["next_target"] == {
        "kind": "verse",
        "reference": "Genesis 1:2",
        "label": "Genesis 1:2",
    }


def test_verses_lookup_chapter_reference(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/verses", params={"q": "Genesis 1"})

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "reference"
    assert body["reference"] == "Genesis 1:1-4"
    assert body["scope"] == "chapter"
    assert [verse["reference"] for verse in body["verses"]] == [
        "Genesis 1:1",
        "Genesis 1:2",
        "Genesis 1:3",
        "Genesis 1:4",
    ]


def test_verses_lookup_text_intent_for_non_reference(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/verses", params={"q": "created heaven"})

    assert response.status_code == 200
    assert response.json() == {
        "intent": "text",
        "query": "created heaven",
        "reference": None,
        "scope": None,
        "previous_target": None,
        "expand_target": None,
        "next_target": None,
        "verses": [],
    }


def test_verses_lookup_rejects_blank_query(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/verses", params={"q": "   "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide a query in the 'q' query param."


def test_verse_search_filters_and_clamps_page(client, db_session):
    seed_bible(db_session)

    response = client.get(
        "/api/verses/search",
        params={
            "q": "God world",
            "book": "John",
            "testament": "nt",
            "page": -5,
            "translation": "esv",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["page"] == 1
    assert body["total"] == 2
    assert [result["reference"] for result in body["results"]] == [
        "John 3:16",
        "John 3:17",
    ]


def test_verse_search_rejects_punctuation_only_non_exact_query(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/verses/search", params={"q": "!!!"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide a non-empty search query."


def test_verse_translations_are_distinct_and_sorted(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/verses/translations")

    assert response.status_code == 200
    assert response.json() == {"translations": ["ESV", "KJV"]}


def test_verse_notes_crud_and_validation(client, db_session):
    seed_bible(db_session)
    seed_verse_notes(db_session)

    missing_verse = client.post("/api/verses/notes", json={"note_markdown": "No verse"})
    assert missing_verse.status_code == 400
    assert missing_verse.json()["detail"] == "verse_id is required."

    invalid_verse = client.post(
        "/api/verses/notes",
        json={"verse_id": 999, "note_markdown": "Bad verse"},
    )
    assert invalid_verse.status_code == 400
    assert invalid_verse.json()["detail"] == "verse_id is invalid."

    created = client.post(
        "/api/verses/notes",
        json={"verse_id": 2, "note_markdown": "Fresh note"},
    )
    assert created.status_code == 201
    note_id = created.json()["note_id"]

    listed = client.get("/api/verses/notes", params={"verse_id": 2})
    assert listed.status_code == 200
    assert [note["note_markdown"] for note in listed.json()] == ["Fresh note"]

    patched = client.patch(
        f"/api/verses/notes/{note_id}",
        json={"note_markdown": "Patched note"},
    )
    assert patched.status_code == 200
    assert patched.json()["note_markdown"] == "Patched note"

    deleted = client.delete(f"/api/verses/notes/{note_id}")
    assert deleted.status_code == 204
    assert db_session.scalar(select(VerseNotes).where(VerseNotes.note_id == note_id)) is None


def test_verse_notes_404_for_unknown_note(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/verses/notes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Verse note not found."


def test_commentaries_and_crossrefs_for_reference(client, db_session):
    seed_bible(db_session)
    seed_commentary_and_crossrefs(db_session)

    commentary_response = client.get(
        "/api/verses/commentaries",
        params={"ref": "Genesis 1:1"},
    )
    assert commentary_response.status_code == 200
    commentary = commentary_response.json()
    assert commentary["count"] == 1
    assert commentary["items"][0]["display_name"] == "Augustine of Hippo"

    crossrefs_response = client.get(
        "/api/verses/crossrefs",
        params={"ref": "Genesis 1:1"},
    )
    assert crossrefs_response.status_code == 200
    crossrefs = crossrefs_response.json()
    assert crossrefs["verses"][0]["cross_references"][0]["reference"] == "John 3:16-17"
    assert crossrefs["footnote_verses"][0]["cross_references"][0]["reference"] == "John 3:16"


def test_commentaries_reject_blank_reference(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/verses/commentaries", params={"ref": " "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide a reference in the 'ref' query param."


def test_verses_sermons_returns_overlapping_sermons(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get("/api/verses/sermons", params={"ref": "Genesis 1:2"})

    assert response.status_code == 200
    assert response.json()["sermons"] == [
        {
            "sermon_id": 10,
            "title": "Creation and Light",
            "preached_on": "2024-02-04",
            "speaker_name": "Ada",
            "series_name": "Beginnings",
            "reference": "Genesis 1:1-3",
            "context_note": "Creation opening",
            "start_verse_id": 1,
            "end_verse_id": 3,
        }
    ]
