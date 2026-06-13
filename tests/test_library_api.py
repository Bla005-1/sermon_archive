from __future__ import annotations

from pathlib import Path

from app.db.models import LibraryItemFiles
from tests.factories import seed_library


def test_library_items_list_and_retrieve(client, db_session):
    seed_library(db_session)

    response = client.get("/api/library/items")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Institutes"
    assert response.json()[0]["files"][0]["original_filename"] == "institutes.pdf"

    retrieve = client.get("/api/library/items/100")
    assert retrieve.status_code == 200
    assert retrieve.json()["author_name"] == "John Calvin"

    missing = client.get("/api/library/items/999")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Library item not found."


def test_library_item_file_upload_download_and_preview(client, db_session, tmp_path):
    seed_library(db_session)
    stored_file = Path(tmp_path, "library", "100", "institutes.pdf")
    stored_file.parent.mkdir(parents=True)
    stored_file.write_bytes(b"%PDF-1.4 test")

    upload = client.post(
        "/api/library/items/100/files",
        files={
            "file": (
                "outline.docx",
                b"docx bytes",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert upload.status_code == 201
    assert upload.json()["original_filename"] == "outline.docx"
    assert Path(tmp_path, upload.json()["relative_path"]).is_file()

    download = client.get("/api/library/items/100/files/110/download")
    assert download.status_code == 200
    assert download.content == b"%PDF-1.4 test"
    assert download.headers["content-disposition"].startswith("attachment;")

    preview = client.get("/api/library/items/100/files/110/preview")
    assert preview.status_code == 200
    assert preview.content == b"%PDF-1.4 test"
    assert preview.headers["content-disposition"].startswith("inline;")


def test_library_item_units_can_return_requested_root_type(client, db_session):
    seed_library(db_session)

    full = client.get("/api/library/items/100/units")
    assert full.status_code == 200
    assert full.json()[0]["unit_type"] == "chapter"
    assert full.json()[0]["children"][0]["unit_type"] == "section"

    sections = client.get("/api/library/items/100/units?root_unit_type=section")
    assert sections.status_code == 200
    assert sections.json()[0]["unit_type"] == "section"
    assert sections.json()[0]["children"][0]["unit_type"] == "paragraph"

    invalid = client.get("/api/library/items/100/units?root_unit_type=heading")
    assert invalid.status_code == 422


def test_library_item_file_preview_rejects_non_preview_types(
    client, db_session, tmp_path
):
    seed_library(db_session)
    text_file = Path(tmp_path, "library", "100", "notes.txt")
    text_file.parent.mkdir(parents=True)
    text_file.write_text("not actually a pdf", encoding="utf-8")
    db_session.add(
        LibraryItemFiles(
            library_item_file_id=111,
            library_item_id=100,
            relative_path="library/100/notes.txt",
            original_filename="notes.txt",
            mime_type="text/plain",
            byte_size=18,
        )
    )
    db_session.commit()

    response = client.get("/api/library/items/100/files/111/preview")
    assert response.status_code == 415
    assert response.json()["detail"] == "File type cannot be previewed."
