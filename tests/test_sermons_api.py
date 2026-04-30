from __future__ import annotations

from datetime import date

from sqlalchemy import select

from app.db.models import SermonPassages, Sermons
from tests.factories import seed_bible, seed_sermons


def test_sermons_list_orders_newest_first_and_filters(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get("/api/sermons", params={"q": "creation"})

    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body] == ["Creation and Light"]
    assert body[0]["attachments"][0]["original_filename"] == "notes.txt"
    assert [p["reference_text"] for p in body[0]["passages"]] == [
        "Genesis 1:4",
        "Genesis 1:1-3",
    ]


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
            "passages": [{"reference_text": "Genesis 1:1"}],
            "attachments": [{"original_filename": "ignored.txt"}],
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sermon_id"] is not None
    assert body["title"] == "A New Sermon"
    assert body["preached_on"] is not None
    assert body["passages"] == []
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


def test_sermon_passage_crud_and_reference_validation(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    missing_reference = client.post(
        "/api/sermons/10/passages",
        json={"context_note": "No reference"},
    )
    assert missing_reference.status_code == 400
    assert (
        missing_reference.json()["detail"]
        == "start_verse_id or reference_text is required."
    )

    created = client.post(
        "/api/sermons/10/passages",
        json={"reference_text": "Genesis 1:2-3", "context_note": "Middle"},
    )
    assert created.status_code == 201
    created_body = created.json()
    assert created_body["reference_text"] == "Genesis 1:2-3"
    assert created_body["display_order"] == 3

    patched = client.patch(
        f"/api/sermons/10/passages/{created_body['sermon_passage_id']}",
        json={"context_note": "Updated middle"},
    )
    assert patched.status_code == 200
    assert patched.json()["context_note"] == "Updated middle"

    deleted = client.delete(
        f"/api/sermons/10/passages/{created_body['sermon_passage_id']}"
    )
    assert deleted.status_code == 204
    assert (
        db_session.scalar(
            select(SermonPassages).where(
                SermonPassages.sermon_passage_id
                == created_body["sermon_passage_id"]
            )
        )
        is None
    )


def test_sermon_passage_is_scoped_to_sermon(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get("/api/sermons/11/passages/20")

    assert response.status_code == 404
    assert response.json()["detail"] == "Sermon passage not found."
