from __future__ import annotations

from sqlalchemy import select

from app.db.models import WidgetPassages
from tests.factories import seed_bible, seed_widget


def test_widget_list_and_retrieve(client, db_session):
    seed_bible(db_session)
    seed_widget(db_session)

    list_response = client.get("/api/widget")
    assert list_response.status_code == 200
    assert list_response.json()[0]["reference_text"] == "Genesis 1:1-2"

    retrieve_response = client.get("/api/widget/50")
    assert retrieve_response.status_code == 200
    assert retrieve_response.json()["start_verse"]["book"]["book_name"] == "Genesis"


def test_widget_create_requires_verse_ids_and_required_text(client, db_session):
    seed_bible(db_session)

    missing_ids = client.post(
        "/api/widget",
        json={
            "translation": "ESV",
            "reference_text": "Genesis 1:1",
            "display_text": "In the beginning",
        },
    )
    assert missing_ids.status_code == 400
    assert (
        missing_ids.json()["detail"]
        == "start_verse_id and end_verse_id are required."
    )

    missing_text = client.post(
        "/api/widget",
        json={
            "start_verse_id": 1,
            "end_verse_id": 1,
            "translation": "",
            "reference_text": "Genesis 1:1",
            "display_text": "In the beginning",
        },
    )
    assert missing_text.status_code == 400
    assert (
        missing_text.json()["detail"]
        == "translation, reference_text, and display_text are required."
    )


def test_widget_create_updates_existing_unique_range(client, db_session):
    seed_bible(db_session)
    seed_widget(db_session)

    response = client.post(
        "/api/widget",
        json={
            "start_verse_id": 1,
            "end_verse_id": 2,
            "translation": "ESV",
            "reference_text": "Genesis 1:1-2",
            "display_text": "Updated display",
            "weight": 8,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["widget_passage_id"] == 50
    assert body["display_text"] == "Updated display"
    assert body["weight"] == 8


def test_widget_patch_validates_new_verse_ids(client, db_session):
    seed_bible(db_session)
    seed_widget(db_session)

    response = client.patch("/api/widget/50", json={"start_verse_id": 999})

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid start_verse_id or end_verse_id."


def test_widget_update_and_delete(client, db_session):
    seed_bible(db_session)
    seed_widget(db_session)

    update_response = client.put(
        "/api/widget/50",
        json={
            "start_verse_id": 100,
            "end_verse_id": 101,
            "translation": "ESV",
            "reference_text": "John 3:16-17",
            "display_text": "For God so loved...",
            "weight": 2,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["reference_text"] == "John 3:16-17"

    delete_response = client.delete("/api/widget/50")
    assert delete_response.status_code == 204
    assert (
        db_session.scalar(
            select(WidgetPassages).where(WidgetPassages.widget_passage_id == 50)
        )
        is None
    )


def test_widget_retrieve_404(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/widget/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Widget entry not found."
