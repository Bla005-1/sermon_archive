from __future__ import annotations

from pathlib import Path

from sqlalchemy import select

from app.db.models import SermonAttachments
from tests.factories import seed_bible, seed_sermons


def test_sermon_attachments_list_and_missing_sermon(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get("/api/sermons/10/attachments")
    assert response.status_code == 200
    assert response.json()[0]["original_filename"] == "notes.txt"

    missing = client.get("/api/sermons/999/attachments")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Sermon not found."


def test_attachment_upload_requires_file(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.post("/api/sermons/10/attachments")

    assert response.status_code == 400
    assert response.json()["detail"] == "Please include a file upload."


def test_attachment_upload_persists_metadata_and_file(client, db_session, tmp_path):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.post(
        "/api/sermons/10/attachments",
        files={"file": ("outline.md", b"# Outline", "text/markdown")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["sermon_id"] == 10
    assert body["original_filename"] == "outline.md"
    assert body["mime_type"] == "text/markdown"
    assert body["byte_size"] == 9
    assert Path(tmp_path, body["relative_path"]).is_file()


def test_attachment_download_is_scoped_to_sermon(client, db_session, tmp_path):
    seed_bible(db_session)
    seed_sermons(db_session)
    stored_file = Path(tmp_path, "2024", "10", "notes.txt")
    stored_file.parent.mkdir(parents=True)
    stored_file.write_text("hello notes", encoding="utf-8")

    response = client.get("/api/sermons/10/attachments/30/download")
    assert response.status_code == 200
    assert response.content == b"hello notes"
    assert response.headers["content-type"] == "text/plain; charset=utf-8"

    wrong_sermon = client.get("/api/sermons/11/attachments/30/download")
    assert wrong_sermon.status_code == 404
    assert wrong_sermon.json()["detail"] == "Attachment not found."


def test_attachment_download_404_when_file_missing(client, db_session):
    seed_bible(db_session)
    seed_sermons(db_session)

    response = client.get("/api/sermons/10/attachments/30/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment file not found."


def test_attachment_update_patch_and_delete(client, db_session, tmp_path):
    seed_bible(db_session)
    seed_sermons(db_session)
    stored_file = Path(tmp_path, "2024", "10", "notes.txt")
    stored_file.parent.mkdir(parents=True)
    stored_file.write_text("delete me", encoding="utf-8")

    update_response = client.put(
        "/api/attachments/30",
        json={
            "attachment_id": 30,
            "sermon_id": 10,
            "relative_path": "ignored",
            "original_filename": "updated.txt",
            "mime_type": "text/plain",
            "byte_size": 20,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["original_filename"] == "updated.txt"

    patch_response = client.patch("/api/attachments/30", json={"byte_size": 9})
    assert patch_response.status_code == 200
    assert patch_response.json()["byte_size"] == 9

    delete_response = client.delete("/api/attachments/30")
    assert delete_response.status_code == 204
    assert not stored_file.exists()
    assert (
        db_session.scalar(
            select(SermonAttachments).where(SermonAttachments.attachment_id == 30)
        )
        is None
    )


def test_attachment_retrieve_404(client, db_session):
    seed_bible(db_session)

    response = client.get("/api/attachments/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment not found."
