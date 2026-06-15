from __future__ import annotations

import datetime as dt
from pathlib import Path

from sqlalchemy import select

from app.db.models import (
    LibraryItems,
    LibraryItemsContentType,
    LibraryItemUnits,
    LibraryItemUnitsUnitType,
    ScriptureReferences,
    SermonPassages,
    Sermons,
)
from app.services.scripture_extraction_service import extract_references_from_text
from tests.factories import seed_scripture_extraction_bible


def test_extract_references_handles_aliases_groups_and_context_shorthand(db_session):
    seed_scripture_extraction_bible(db_session)

    response = extract_references_from_text(
        db_session,
        (
            "Knowledge puffs up (1 Cor 8:1-2). "
            "Jesus speaks (Jn 14:9, 6). "
            "Look at Psalm 119: the psalmist says this (vv. 12, 18, 97). "
            "Christ sat down (Heb 1:3; 8:1)."
        ),
    )

    assert [
        reference.reference_text for reference in response.references
    ] == [
        "1 Corinthians 8:1-2",
        "John 14:9",
        "John 14:6",
        "Psalms 119:1-125",
        "Psalms 119:12",
        "Psalms 119:18",
        "Psalms 119:97",
        "Hebrews 1:3",
        "Hebrews 8:1",
    ]
    assert response.unresolved == []


def test_preview_endpoint_reports_unresolved_candidates(client, db_session):
    seed_scripture_extraction_bible(db_session)

    response = client.post(
        "/api/scripture/extract",
        json={"text": "Known (Jn 17:3). Missing (Jn 99:99)."},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["reference_text"] for item in body["references"]] == ["John 17:3"]
    assert body["unresolved"][0]["matched_text"] == "Jn 99:99"


def test_library_unit_extraction_is_structure_aware(client, db_session):
    seed_scripture_extraction_bible(db_session)
    item = LibraryItems(
        library_item_id=200,
        title="Knowing God",
        content_type=LibraryItemsContentType.BOOK,
    )
    chapter = LibraryItemUnits(
        library_item_unit_id=201,
        library_item_id=200,
        unit_order=1,
        unit_type=LibraryItemUnitsUnitType.CHAPTER,
        unit_title="Chapter 1: The Study of God",
    )
    section = LibraryItemUnits(
        library_item_unit_id=202,
        library_item_id=200,
        parent_library_item_unit_id=201,
        unit_order=2,
        unit_type=LibraryItemUnitsUnitType.SECTION,
        unit_title="Knowledge Applied",
    )
    paragraph = LibraryItemUnits(
        library_item_unit_id=203,
        library_item_id=200,
        parent_library_item_unit_id=202,
        unit_order=3,
        unit_type=LibraryItemUnitsUnitType.PARAGRAPH,
        content_text_markdown=Path("tests/library_snippet.txt").read_text(
            encoding="utf-8"
        ).splitlines()[45],
    )
    db_session.add_all([item, chapter, section, paragraph])
    db_session.commit()

    response = client.post(
        "/api/library/items/200/units/201/scripture-references/extract"
    )

    assert response.status_code == 200
    body = response.json()
    refs = [item["reference_text"] for item in body["references"]]
    assert "1 Corinthians 8:1-2" in refs
    assert body["references"][0]["source_id"] == 203
    assert (
        db_session.scalar(
            select(ScriptureReferences).where(
                ScriptureReferences.source_id == 201
            )
        )
        is None
    )

    listed = client.get("/api/library/items/200/units/201/scripture-references")
    assert listed.status_code == 200
    assert [item["reference_text"] for item in listed.json()] == refs


def test_sermon_extraction_persists_without_changing_sermon_passages(client, db_session):
    seed_scripture_extraction_bible(db_session)
    sermon = Sermons(
        sermon_id=300,
        preached_on=dt.date(2024, 1, 1),
        title="Known By God",
        notes_markdown="We are known by God (Jn 17:3; 14:6). Also see Hab 3:17-19.",
    )
    db_session.add(sermon)
    db_session.commit()

    response = client.post("/api/sermons/300/scripture-references/extract")

    assert response.status_code == 200
    refs = [item["reference_text"] for item in response.json()["references"]]
    assert refs == ["John 17:3", "John 14:6", "Habakkuk 3:17-19"]
    assert (
        db_session.scalar(
            select(SermonPassages).where(SermonPassages.sermon_id == 300)
        )
        is None
    )

    listed = client.get("/api/sermons/300/scripture-references")
    assert listed.status_code == 200
    assert [item["reference_text"] for item in listed.json()] == refs
