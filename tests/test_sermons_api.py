from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.db.models import ScriptureReferences, ScriptureReferencesSourceType, Sermons
from tests.factories import seed_bible, seed_sermons


def test_sermons_list_orders_newest_first_and_filters(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get("/api/sermons", params={"q": "creation"})

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body] == ["Creation and Light"]
    assert body[0]["attachments"][0]["original_filename"] == "notes.txt"
    assert "passages" not in body[0]


def test_sermons_browse_by_time_orders_newest_first_and_filters(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get(
        "/api/sermons/browse",
        params={
            "type": "time",
            "year": 2024,
            "speaker": "Ada",
            "series": "Beginnings",
            "location": "Main Hall",
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "sermon_id": 10,
            "title": "Creation and Light",
            "speaker_name": "Ada",
            "preached_on": "2024-02-04",
            "order_number": 1,
        }
    ]


def test_sermons_browse_by_scripture_orders_canonically(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)
    db_session.add(
        Sermons(
            sermon_id=12,
            preached_on=date(2024, 4, 1),
            title="Earlier Text Later Date",
            speaker_name="Ada",
            series_name="Beginnings",
            location_name="Main Hall",
        )
    )
    db_session.flush()
    db_session.add(
        ScriptureReferences(
            scripture_reference_id=23,
            source_type=ScriptureReferencesSourceType.SERMON,
            source_id=12,
            start_verse_id=1,
            end_verse_id=3,
            reference_text="Genesis 1:1-3",
            matched_text="Genesis 1:1-3",
            display_order=1,
        )
    )
    db_session.commit()

    response = client.get("/api/sermons/browse", params={"type": "scripture"})

    assert response.status_code == 200
    body = response.json()
    assert [
        (item["sermon_id"], item["reference"], item["order_number"])
        for item in body
    ] == [
        (12, "Genesis 1:1-3", 1),
        (10, "Genesis 1:1-3", 2),
        (10, "Genesis 1:4", 3),
        (11, "John 3:16-17", 4),
    ]


def test_sermons_browse_by_scripture_applies_exact_filters(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get(
        "/api/sermons/browse",
        params={
            "type": "scripture",
            "year": 2024,
            "speaker": "Ben",
            "series": "John",
            "location": "Chapel",
        },
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "sermon_id": 11,
            "title": "Love and Judgment",
            "speaker_name": "Ben",
            "preached_on": "2024-03-10",
            "order_number": 1,
            "reference": "John 3:16-17",
        }
    ]


def test_sermons_browse_rejects_invalid_type(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/sermons/browse", params={"type": "author"})

    assert response.status_code == 422


def test_sermons_create_requires_non_blank_title(client):
    response = client.post("/api/sermons", json={"title": ""})

    assert response.status_code == 400
    assert response.json()["detail"] == "title is required."


def test_sermons_create_defaults_preached_on_and_returns_nested_lists(client, db_session):
    seed_bible(db_session)

    response = client.post(
        "/api/sermons",
        json={
            "title": "A New Sermon",
            "speaker_name": "Ada",
            "attachments": [{"original_filename": "ignored.txt"}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sermon_id"] is not None
    assert body["title"] == "A New Sermon"
    assert body["preached_on"] is not None
    assert body["attachments"] == []


def test_sermons_retrieve_404(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/sermons/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Sermon not found."


def test_sermons_update_and_patch_validate_title(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    blank_patch = client.patch("/api/sermons/10", json={"title": ""})
    assert blank_patch.status_code == 400
    assert blank_patch.json()["detail"] == "title cannot be blank."

    update_response = client.put(
        "/api/sermons/10",
        json={
            "title": "Updated Title",
            "preached_on": "2024-04-01",
            "speaker_name": "Cara",
            "series_name": None,
            "location_name": "Sanctuary",
            "notes_markdown": "Updated notes",
        },
    )

    assert update_response.status_code == 200
    body = update_response.json()
    assert body["title"] == "Updated Title"
    assert body["speaker_name"] == "Cara"


def test_sermons_delete_removes_row(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.delete("/api/sermons/11")

    assert response.status_code == 204
    assert db_session.scalar(select(Sermons).where(Sermons.sermon_id == 11)) is None


def test_sermon_suggestions_exclude_blank_values_and_order_by_recent(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)
    db_session.add(
        Sermons(
            sermon_id=12,
            preached_on=date(2024, 4, 1),
            title="Silent Metadata",
            speaker_name="",
            series_name=None,
            location_name="Chapel",
        )
    )
    db_session.commit()

    response = client.get("/api/sermons/suggestions")

    assert response.status_code == 200
    assert response.json() == {
        "speakers": ["Ben", "Ada"],
        "series": ["John", "Beginnings"],
        "locations": ["Chapel", "Main Hall"],
    }
