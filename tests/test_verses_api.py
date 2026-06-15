from __future__ import annotations

from sqlalchemy import select

from app.db.models import (
    LibraryItemUnits,
    ScriptureReferences,
    ScriptureReferencesSourceType,
    VerseNotes,
)
from tests.factories import (
    seed_bible,
    seed_commentary_and_crossrefs,
    seed_library,
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


def test_verses_reference_gets_reference_without_text_intent(client, db_session):
    seed_bible(db_session)

    response = client.get(
        "/api/verses/reference",
        params={"ref": "Genesis 1:1", "translation": "kjv"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["intent"] == "reference"
    assert body["reference"] == "Genesis 1:1"
    assert body["scope"] == "verse"
    assert body["verses"][0]["translation"] == "KJV"

    non_reference = client.get(
        "/api/verses/reference",
        params={"ref": "created heaven"},
    )
    assert non_reference.status_code == 400
    assert "References should be formatted" in non_reference.json()["detail"]


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


def test_verses_sermons_returns_overlapping_scripture_references(client, db_session):
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


def test_verses_sermons_rejects_bad_reference(client, db_session):
    seed_bible(db_session)

    blank = client.get("/api/verses/sermons", params={"ref": " "})
    assert blank.status_code == 400
    assert blank.json()["detail"] == "Provide a reference in the 'ref' query param."

    invalid = client.get("/api/verses/sermons", params={"ref": "Genesis 99:99"})
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "We could not locate that verse in the archive."


def test_verses_library_items_returns_overlapping_units(client, db_session):
    seed_bible(db_session)
    seed_library(db_session)
    paragraph = db_session.scalar(
        select(LibraryItemUnits).where(LibraryItemUnits.library_item_unit_id == 122)
    )
    paragraph.unit_title = "Opening paragraph"
    paragraph.source_start_page_number = 7
    paragraph.source_end_page_number = 8
    db_session.add(
        ScriptureReferences(
            scripture_reference_id=91,
            source_type=ScriptureReferencesSourceType.LIBRARY_ITEM_UNIT,
            source_id=122,
            start_verse_id=1,
            end_verse_id=3,
            reference_text="Genesis 1:1-3",
            matched_text="Gen 1:1-3",
            context_text="Chapter 1 > Section 1",
            display_order=1,
        )
    )
    db_session.commit()

    response = client.get("/api/verses/library-items", params={"ref": "Genesis 1:2"})

    assert response.status_code == 200
    assert response.json() == {
        "reference": "Genesis 1:2",
        "library_items": [
            {
                "library_item_id": 100,
                "library_item_unit_id": 122,
                "title": "Institutes",
                "content_type": "book",
                "author_name": "John Calvin",
                "unit_title": "Opening paragraph",
                "unit_type": "paragraph",
                "unit_order": 3,
                "source_start_page_number": 7,
                "source_end_page_number": 8,
                "reference": "Genesis 1:1-3",
                "context_text": "Chapter 1 > Section 1",
                "start_verse_id": 1,
                "end_verse_id": 3,
                "chapter_title": "Chapter 1",
                "chapter_unit_id": 120,
                "section_title": "Section 1",
                "section_unit_id": 121,
            }
        ],
    }


def test_verses_library_items_rejects_bad_reference_and_returns_empty(
    client, db_session
):
    seed_bible(db_session)
    seed_library(db_session)

    blank = client.get("/api/verses/library-items", params={"ref": " "})
    assert blank.status_code == 400
    assert blank.json()["detail"] == "Provide a reference in the 'ref' query param."

    invalid = client.get("/api/verses/library-items", params={"ref": "Genesis 99:99"})
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "We could not locate that verse in the archive."

    empty = client.get("/api/verses/library-items", params={"ref": "John 3:16"})
    assert empty.status_code == 200
    assert empty.json() == {"reference": "John 3:16", "library_items": []}
