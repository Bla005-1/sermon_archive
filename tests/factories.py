from __future__ import annotations

import datetime as dt
from sqlalchemy.orm import Session

from app.db.models import (
    ApiAccessTokens,
    ApiSessions,
    ApiUsers,
    BibleBooks,
    BibleBooksTestament,
    BibleVerses,
    ChurchFathers,
    Commentaries,
    FootnoteCrossReferences,
    LibraryItemFiles,
    LibraryItems,
    LibraryItemsContentType,
    LibraryItemUnits,
    LibraryItemUnitsUnitType,
    MlCrossReferences,
    SermonAttachments,
    SermonPassages,
    Sermons,
    VerseFootnotes,
    VerseHeadings,
    VerseNotes,
    VerseTexts,
    WidgetPassages,
)


def seed_bible(db: Session) -> dict[str, BibleVerses]:
    genesis = BibleBooks(
        book_id=1,
        book_name="Genesis",
        book_order=1,
        testament=BibleBooksTestament.OT,
    )
    john = BibleBooks(
        book_id=43,
        book_name="John",
        book_order=43,
        testament=BibleBooksTestament.NT,
    )
    verses = {
        "gen_1_1": BibleVerses(verse_id=1, book_id=1, chapter_number=1, verse_number=1),
        "gen_1_2": BibleVerses(verse_id=2, book_id=1, chapter_number=1, verse_number=2),
        "gen_1_3": BibleVerses(verse_id=3, book_id=1, chapter_number=1, verse_number=3),
        "gen_1_4": BibleVerses(verse_id=4, book_id=1, chapter_number=1, verse_number=4),
        "john_3_16": BibleVerses(
            verse_id=100, book_id=43, chapter_number=3, verse_number=16
        ),
        "john_3_17": BibleVerses(
            verse_id=101, book_id=43, chapter_number=3, verse_number=17
        ),
    }
    db.add_all([genesis, john, *verses.values()])
    db.flush()

    db.add_all(
        [
            VerseTexts(
                verse_text_id=1,
                verse_id=1,
                translation="KJV",
                marked_text="In the beginning",
                plain_text="In the beginning God created the heaven and the earth.",
            ),
            VerseTexts(
                verse_text_id=2,
                verse_id=1,
                translation="ESV",
                marked_text="In the beginning",
                plain_text="In the beginning, God created the heavens and the earth.",
            ),
            VerseTexts(
                verse_text_id=3,
                verse_id=2,
                translation="ESV",
                marked_text="The earth was without form",
                plain_text="The earth was without form and void.",
            ),
            VerseTexts(
                verse_text_id=4,
                verse_id=3,
                translation="ESV",
                marked_text="Let there be light",
                plain_text="And God said, Let there be light.",
            ),
            VerseTexts(
                verse_text_id=5,
                verse_id=4,
                translation="ESV",
                marked_text="God saw that the light was good",
                plain_text="And God saw that the light was good.",
            ),
            VerseTexts(
                verse_text_id=6,
                verse_id=100,
                translation="ESV",
                marked_text="For God so loved the world",
                plain_text="For God so loved the world.",
            ),
            VerseTexts(
                verse_text_id=7,
                verse_id=101,
                translation="ESV",
                marked_text="For God did not send his Son",
                plain_text="For God did not send his Son into the world to condemn the world.",
            ),
        ]
    )
    db.commit()
    return verses


def seed_scripture_extraction_bible(db: Session) -> dict[str, BibleVerses]:
    books = [
        (1, "Genesis", BibleBooksTestament.OT),
        (2, "Exodus", BibleBooksTestament.OT),
        (19, "Psalms", BibleBooksTestament.OT),
        (23, "Isaiah", BibleBooksTestament.OT),
        (24, "Jeremiah", BibleBooksTestament.OT),
        (35, "Habakkuk", BibleBooksTestament.OT),
        (40, "Matthew", BibleBooksTestament.NT),
        (43, "John", BibleBooksTestament.NT),
        (45, "Romans", BibleBooksTestament.NT),
        (46, "1 Corinthians", BibleBooksTestament.NT),
        (47, "2 Corinthians", BibleBooksTestament.NT),
        (50, "Philippians", BibleBooksTestament.NT),
        (53, "2 Thessalonians", BibleBooksTestament.NT),
        (58, "Hebrews", BibleBooksTestament.NT),
        (62, "1 John", BibleBooksTestament.NT),
    ]
    db.add_all(
        [
            BibleBooks(
                book_id=book_id,
                book_name=name,
                book_order=book_id,
                testament=testament,
            )
            for book_id, name, testament in books
        ]
    )
    db.flush()

    locations = [
        (1, 1, 1), (1, 1, 2), (1, 1, 5),
        (2, 20, 2), (2, 20, 3), (2, 20, 4), (2, 20, 5),
        (19, 119, 1), (19, 119, 2), (19, 119, 5), (19, 119, 12),
        (19, 119, 18), (19, 119, 97), (19, 119, 103), (19, 119, 125),
        (23, 44, 9), (23, 44, 20), (23, 46, 6), (23, 46, 7),
        (24, 9, 23), (24, 9, 24),
        (35, 3, 17), (35, 3, 19),
        (40, 16, 16), (40, 22, 37), (40, 22, 38),
        (43, 14, 6), (43, 14, 9), (43, 17, 3),
        (45, 8, 31), (45, 8, 39),
        (46, 8, 1), (46, 8, 2), (46, 10, 13), (46, 15, 47), (46, 15, 54),
        (47, 5, 21), (47, 12, 9),
        (50, 3, 7), (50, 3, 10),
        (53, 2, 10),
        (58, 1, 3), (58, 8, 1), (58, 13, 8),
        (62, 2, 4), (62, 2, 9), (62, 2, 11), (62, 3, 6), (62, 3, 11),
        (62, 4, 20),
    ]
    verses = {
        f"{book_id}_{chapter}_{verse}": BibleVerses(
            verse_id=book_id * 100000 + chapter * 1000 + verse,
            book_id=book_id,
            chapter_number=chapter,
            verse_number=verse,
        )
        for book_id, chapter, verse in locations
    }
    db.add_all(verses.values())
    db.commit()
    return verses


def seed_sermons(db: Session) -> tuple[Sermons, Sermons]:
    first = Sermons(
        sermon_id=10,
        preached_on=dt.date(2024, 2, 4),
        title="Creation and Light",
        speaker_name="Ada",
        series_name="Beginnings",
        location_name="Main Hall",
        notes_markdown="First sermon",
    )
    second = Sermons(
        sermon_id=11,
        preached_on=dt.date(2024, 3, 10),
        title="Love and Judgment",
        speaker_name="Ben",
        series_name="John",
        location_name="Chapel",
        notes_markdown="Second sermon",
    )
    db.add_all([first, second])
    db.flush()
    db.add_all(
        [
            SermonPassages(
                sermon_passage_id=20,
                sermon_id=10,
                start_verse_id=1,
                end_verse_id=3,
                reference_text="Genesis 1:1-3",
                context_note="Creation opening",
                display_order=2,
            ),
            SermonPassages(
                sermon_passage_id=21,
                sermon_id=10,
                start_verse_id=4,
                end_verse_id=None,
                reference_text="Genesis 1:4",
                context_note="Good light",
                display_order=1,
            ),
            SermonPassages(
                sermon_passage_id=22,
                sermon_id=11,
                start_verse_id=100,
                end_verse_id=101,
                reference_text="John 3:16-17",
                context_note="Gospel summary",
                display_order=1,
            ),
            SermonAttachments(
                attachment_id=30,
                sermon_id=10,
                relative_path="2024/10/notes.txt",
                original_filename="notes.txt",
                mime_type="text/plain",
                byte_size=12,
            ),
        ]
    )
    db.commit()
    return first, second


def seed_verse_notes(db: Session) -> tuple[VerseNotes, VerseNotes]:
    first = VerseNotes(note_id=40, verse_id=1, note_markdown="Creation note")
    second = VerseNotes(note_id=41, verse_id=100, note_markdown="Gospel note")
    db.add_all([first, second])
    db.commit()
    return first, second


def seed_commentary_and_crossrefs(db: Session) -> None:
    father = ChurchFathers(
        father_id=1,
        father_name="Augustine",
        default_year=400,
        wiki_url="https://example.test/augustine",
    )
    commentary = Commentaries(
        commentary_id=1,
        father_id=1,
        book_id=1,
        start_verse_id=1,
        end_verse_id=2,
        commentary_text="Creation is ordered.",
        append_to_author_name="of Hippo",
        source_url="https://example.test/source",
        source_title="Commentary",
    )
    crossref = MlCrossReferences(
        ml_cross_reference_id=1,
        source_verse_id=1,
        target_start_verse_id=100,
        target_end_verse_id=101,
        vote_count=9,
        note="Creation and redemption",
    )
    footnote = VerseFootnotes(
        footnote_id=1,
        verse_id=1,
        translation="ESV",
        order_in_translation=1,
        word_index=1,
        footnote_label="a",
        footnote_text="See John 3:16",
    )
    footnote_crossref = FootnoteCrossReferences(
        footnote_cross_reference_id=1,
        footnote_id=1,
        target_start_verse_id=100,
        target_end_verse_id=None,
        source_order_number=1,
        reference_note="alternate",
    )
    db.add_all([father, commentary, crossref, footnote, footnote_crossref])
    db.commit()


def seed_widget(db: Session) -> WidgetPassages:
    widget = WidgetPassages(
        widget_passage_id=50,
        start_verse_id=1,
        end_verse_id=2,
        translation="ESV",
        reference_text="Genesis 1:1-2",
        display_text="In the beginning... The earth was without form.",
        weight=5,
    )
    db.add(widget)
    db.commit()
    return widget


def seed_library(db: Session) -> LibraryItems:
    item = LibraryItems(
        library_item_id=100,
        title="Institutes",
        content_type=LibraryItemsContentType.BOOK,
        author_name="John Calvin",
        description_text="A test library item",
    )
    db.add(item)
    db.flush()
    db.add_all(
        [
            LibraryItemFiles(
                library_item_file_id=110,
                library_item_id=100,
                relative_path="library/100/institutes.pdf",
                original_filename="institutes.pdf",
                mime_type="application/pdf",
                byte_size=13,
            ),
            LibraryItemUnits(
                library_item_unit_id=120,
                library_item_id=100,
                parent_library_item_unit_id=None,
                unit_order=1,
                unit_type=LibraryItemUnitsUnitType.CHAPTER,
                unit_title="Chapter 1",
                content_text="Chapter text",
            ),
            LibraryItemUnits(
                library_item_unit_id=121,
                library_item_id=100,
                parent_library_item_unit_id=120,
                unit_order=2,
                unit_type=LibraryItemUnitsUnitType.SECTION,
                unit_title="Section 1",
                content_text="Section text",
            ),
            LibraryItemUnits(
                library_item_unit_id=122,
                library_item_id=100,
                parent_library_item_unit_id=121,
                unit_order=3,
                unit_type=LibraryItemUnitsUnitType.PARAGRAPH,
                content_text="Paragraph text",
            ),
        ]
    )
    db.commit()
    return item


def seed_user(db: Session, *, active: bool = True) -> ApiUsers:
    user = ApiUsers(
        user_id=1,
        username="reader",
        email="reader@example.test",
        password_hash="test-hash",
        is_active=1 if active else 0,
        is_staff=0,
    )
    db.add(user)
    db.commit()
    return user


def seed_session(
    db: Session, *, expired: bool = False, revoked: bool = False
) -> ApiSessions:
    now = dt.datetime.now(dt.UTC)
    session = ApiSessions(
        session_id="session-1",
        user_id=1,
        csrf_token="csrf-1",
        expires_at=(
            now - dt.timedelta(minutes=1) if expired else now + dt.timedelta(days=1)
        ),
        last_seen_at=now,
        is_revoked=1 if revoked else 0,
    )
    db.add(session)
    db.commit()
    return session


def seed_token(
    db: Session, token_hash: str, *, expired: bool = False
) -> ApiAccessTokens:
    now = dt.datetime.now(dt.UTC)
    token = ApiAccessTokens(
        token_id=1,
        user_id=1,
        token_hash=token_hash,
        token_name="tests",
        expires_at=(
            now - dt.timedelta(minutes=1) if expired else now + dt.timedelta(days=1)
        ),
        last_used_at=now,
    )
    db.add(token)
    db.commit()
    return token
