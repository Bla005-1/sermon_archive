from typing import Optional
import datetime
import enum

from sqlalchemy import (
    Date,
    Enum,
    Float,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    TIMESTAMP,
    Text,
    text,
)
from sqlalchemy.dialects.mysql import BIGINT, INTEGER, LONGTEXT, SMALLINT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class BibleBooksTestament(str, enum.Enum):
    OT = "OT"
    NT = "NT"


class ApiUsers(Base):
    __tablename__ = "api_users"
    __table_args__ = (
        Index("uq_api_users_email", "email", unique=True),
        Index("uq_api_users_username", "username", unique=True),
    )

    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    username: Mapped[str] = mapped_column(String(150), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[int] = mapped_column(
        TINYINT(unsigned=True), nullable=False, server_default=text("'1'")
    )
    is_staff: Mapped[int] = mapped_column(
        TINYINT(unsigned=True), nullable=False, server_default=text("'0'")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
    email: Mapped[Optional[str]] = mapped_column(String(254))
    last_login_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)

    api_access_tokens: Mapped[list["ApiAccessTokens"]] = relationship(
        "ApiAccessTokens", back_populates="user"
    )
    api_sessions: Mapped[list["ApiSessions"]] = relationship(
        "ApiSessions", back_populates="user"
    )


class BibleBooks(Base):
    __tablename__ = "bible_books"
    __table_args__ = (
        Index("idx_bible_books_book_order", "book_order"),
        Index("uq_bible_books_book_name", "book_name", unique=True),
    )

    book_id: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)
    book_name: Mapped[str] = mapped_column(String(64), nullable=False)
    book_order: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    testament: Mapped[BibleBooksTestament] = mapped_column(
        Enum(
            BibleBooksTestament,
            values_callable=lambda cls: [member.value for member in cls],
        ),
        nullable=False,
    )

    bible_verses: Mapped[list["BibleVerses"]] = relationship(
        "BibleVerses", back_populates="book"
    )
    commentaries: Mapped[list["Commentaries"]] = relationship(
        "Commentaries", back_populates="book"
    )


class ChurchFathers(Base):
    __tablename__ = "church_fathers"
    __table_args__ = (
        Index("uq_church_fathers_father_name", "father_name", unique=True),
    )

    father_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    father_name: Mapped[str] = mapped_column(String(128), nullable=False)
    default_year: Mapped[Optional[int]] = mapped_column(Integer)
    wiki_url: Mapped[Optional[str]] = mapped_column(String(512))

    commentaries: Mapped[list["Commentaries"]] = relationship(
        "Commentaries", back_populates="father"
    )


class Sermons(Base):
    __tablename__ = "sermons"
    __table_args__ = (
        Index("idx_sermons_preached_on", "preached_on"),
        Index("idx_sermons_speaker_preached_on", "speaker_name", "preached_on"),
    )

    sermon_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    preached_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    speaker_name: Mapped[Optional[str]] = mapped_column(String(128))
    series_name: Mapped[Optional[str]] = mapped_column(String(128))
    location_name: Mapped[Optional[str]] = mapped_column(String(128))
    notes_markdown: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    )

    sermon_attachments: Mapped[list["SermonAttachments"]] = relationship(
        "SermonAttachments", back_populates="sermon"
    )
    sermon_passages: Mapped[list["SermonPassages"]] = relationship(
        "SermonPassages", back_populates="sermon"
    )


class ApiAccessTokens(Base):
    __tablename__ = "api_access_tokens"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["api_users.user_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_api_access_tokens_user",
        ),
        Index("idx_api_access_tokens_expires", "expires_at"),
        Index("idx_api_access_tokens_user", "user_id"),
        Index("uq_api_access_tokens_hash", "token_hash", unique=True),
    )

    token_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False)
    token_name: Mapped[Optional[str]] = mapped_column(String(128))
    last_used_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)
    revoked_at: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)
    scopes: Mapped[Optional[str]] = mapped_column(String(512))

    user: Mapped["ApiUsers"] = relationship(
        "ApiUsers", back_populates="api_access_tokens"
    )


class ApiSessions(Base):
    __tablename__ = "api_sessions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["user_id"],
            ["api_users.user_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_api_sessions_user",
        ),
        Index("idx_api_sessions_expires", "expires_at"),
        Index("idx_api_sessions_user", "user_id"),
    )

    session_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    csrf_token: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False)
    last_seen_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    is_revoked: Mapped[int] = mapped_column(
        TINYINT(unsigned=True), nullable=False, server_default=text("'0'")
    )
    ip_address: Mapped[Optional[str]] = mapped_column(String(64))
    user_agent: Mapped[Optional[str]] = mapped_column(String(512))

    user: Mapped["ApiUsers"] = relationship("ApiUsers", back_populates="api_sessions")


class BibleVerses(Base):
    __tablename__ = "bible_verses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["book_id"],
            ["bible_books.book_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_bible_verses_book",
        ),
        Index("idx_bible_verses_book_chapter", "book_id", "chapter_number"),
        Index(
            "uq_bible_verses_location",
            "book_id",
            "chapter_number",
            "verse_number",
            unique=True,
        ),
    )

    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    book_id: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    chapter_number: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False)
    verse_number: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False)
    weight: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("'1'")
    )

    book: Mapped["BibleBooks"] = relationship(
        "BibleBooks", back_populates="bible_verses"
    )
    commentaries_end_verse: Mapped[list["Commentaries"]] = relationship(
        "Commentaries",
        foreign_keys="[Commentaries.end_verse_id]",
        back_populates="end_verse",
    )
    commentaries_start_verse: Mapped[list["Commentaries"]] = relationship(
        "Commentaries",
        foreign_keys="[Commentaries.start_verse_id]",
        back_populates="start_verse",
    )
    ml_cross_references_source_verse: Mapped[list["MlCrossReferences"]] = relationship(
        "MlCrossReferences",
        foreign_keys="[MlCrossReferences.source_verse_id]",
        back_populates="source_verse",
    )
    ml_cross_references_target_end_verse: Mapped[list["MlCrossReferences"]] = (
        relationship(
            "MlCrossReferences",
            foreign_keys="[MlCrossReferences.target_end_verse_id]",
            back_populates="target_end_verse",
        )
    )
    ml_cross_references_target_start_verse: Mapped[list["MlCrossReferences"]] = (
        relationship(
            "MlCrossReferences",
            foreign_keys="[MlCrossReferences.target_start_verse_id]",
            back_populates="target_start_verse",
        )
    )
    sermon_passages_end_verse: Mapped[list["SermonPassages"]] = relationship(
        "SermonPassages",
        foreign_keys="[SermonPassages.end_verse_id]",
        back_populates="end_verse",
    )
    sermon_passages_start_verse: Mapped[list["SermonPassages"]] = relationship(
        "SermonPassages",
        foreign_keys="[SermonPassages.start_verse_id]",
        back_populates="start_verse",
    )
    verse_footnotes: Mapped[list["VerseFootnotes"]] = relationship(
        "VerseFootnotes", back_populates="verse"
    )
    verse_headings: Mapped[list["VerseHeadings"]] = relationship(
        "VerseHeadings", back_populates="start_verse"
    )
    verse_notes: Mapped[list["VerseNotes"]] = relationship(
        "VerseNotes", back_populates="verse"
    )
    verse_texts: Mapped[list["VerseTexts"]] = relationship(
        "VerseTexts", back_populates="verse"
    )
    widget_passages_end_verse: Mapped[list["WidgetPassages"]] = relationship(
        "WidgetPassages",
        foreign_keys="[WidgetPassages.end_verse_id]",
        back_populates="end_verse",
    )
    widget_passages_start_verse: Mapped[list["WidgetPassages"]] = relationship(
        "WidgetPassages",
        foreign_keys="[WidgetPassages.start_verse_id]",
        back_populates="start_verse",
    )
    footnote_cross_references_target_end_verse: Mapped[
        list["FootnoteCrossReferences"]
    ] = relationship(
        "FootnoteCrossReferences",
        foreign_keys="[FootnoteCrossReferences.target_end_verse_id]",
        back_populates="target_end_verse",
    )
    footnote_cross_references_target_start_verse: Mapped[
        list["FootnoteCrossReferences"]
    ] = relationship(
        "FootnoteCrossReferences",
        foreign_keys="[FootnoteCrossReferences.target_start_verse_id]",
        back_populates="target_start_verse",
    )


class SermonAttachments(Base):
    __tablename__ = "sermon_attachments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["sermon_id"],
            ["sermons.sermon_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_sermon_attachments_sermon",
        ),
        Index("idx_sermon_attachments_created", "created_at"),
        Index("idx_sermon_attachments_relative_path", "relative_path"),
        Index("idx_sermon_attachments_sermon", "sermon_id"),
    )

    attachment_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    sermon_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(255))
    byte_size: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )

    sermon: Mapped["Sermons"] = relationship(
        "Sermons", back_populates="sermon_attachments"
    )


class Commentaries(Base):
    __tablename__ = "commentaries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["book_id"],
            ["bible_books.book_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_commentaries_book",
        ),
        ForeignKeyConstraint(
            ["end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_commentaries_end_verse",
        ),
        ForeignKeyConstraint(
            ["father_id"],
            ["church_fathers.father_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_commentaries_father",
        ),
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_commentaries_start_verse",
        ),
        Index("idx_commentaries_book", "book_id"),
        Index("idx_commentaries_end_verse", "end_verse_id"),
        Index("idx_commentaries_father", "father_id"),
        Index("idx_commentaries_start_verse", "start_verse_id"),
    )

    commentary_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    father_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    book_id: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    start_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    end_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    commentary_text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    append_to_author_name: Mapped[Optional[str]] = mapped_column(String(255))
    source_url: Mapped[Optional[str]] = mapped_column(String(2048))
    source_title: Mapped[Optional[str]] = mapped_column(String(512))

    book: Mapped["BibleBooks"] = relationship(
        "BibleBooks", back_populates="commentaries"
    )
    end_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[end_verse_id],
        back_populates="commentaries_end_verse",
    )
    father: Mapped["ChurchFathers"] = relationship(
        "ChurchFathers", back_populates="commentaries"
    )
    start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[start_verse_id],
        back_populates="commentaries_start_verse",
    )


class MlCrossReferences(Base):
    __tablename__ = "ml_cross_references"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_ml_cross_references_source_verse",
        ),
        ForeignKeyConstraint(
            ["target_end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_ml_cross_references_target_end",
        ),
        ForeignKeyConstraint(
            ["target_start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_ml_cross_references_target_start",
        ),
        Index("idx_ml_cross_references_target_end", "target_end_verse_id"),
        Index("idx_ml_cross_references_target_start", "target_start_verse_id"),
        Index(
            "uq_ml_cross_references_source_target",
            "source_verse_id",
            "target_start_verse_id",
            "target_end_verse_id",
            unique=True,
        ),
    )

    ml_cross_reference_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True
    )
    source_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    target_start_verse_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), nullable=False
    )
    target_end_verse_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    vote_count: Mapped[Optional[int]] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(String(255))

    source_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[source_verse_id],
        back_populates="ml_cross_references_source_verse",
    )
    target_end_verse: Mapped[Optional["BibleVerses"]] = relationship(
        "BibleVerses",
        foreign_keys=[target_end_verse_id],
        back_populates="ml_cross_references_target_end_verse",
    )
    target_start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[target_start_verse_id],
        back_populates="ml_cross_references_target_start_verse",
    )


class SermonPassages(Base):
    __tablename__ = "sermon_passages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_sermon_passages_end_verse",
        ),
        ForeignKeyConstraint(
            ["sermon_id"],
            ["sermons.sermon_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_sermon_passages_sermon",
        ),
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_sermon_passages_start_verse",
        ),
        Index("idx_sermon_passages_end_verse", "end_verse_id"),
        Index("idx_sermon_passages_start_verse", "start_verse_id"),
        Index(
            "uq_sermon_passages_sermon_display_order",
            "sermon_id",
            "display_order",
            unique=True,
        ),
    )

    sermon_passage_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True
    )
    sermon_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    start_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    end_verse_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    reference_text: Mapped[Optional[str]] = mapped_column(String(64))
    context_note: Mapped[Optional[str]] = mapped_column(String(512))
    display_order: Mapped[Optional[int]] = mapped_column(
        SMALLINT(unsigned=True), server_default=text("'1'")
    )

    end_verse: Mapped[Optional["BibleVerses"]] = relationship(
        "BibleVerses",
        foreign_keys=[end_verse_id],
        back_populates="sermon_passages_end_verse",
    )
    sermon: Mapped["Sermons"] = relationship(
        "Sermons", back_populates="sermon_passages"
    )
    start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[start_verse_id],
        back_populates="sermon_passages_start_verse",
    )


class VerseFootnotes(Base):
    __tablename__ = "verse_footnotes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_verse_footnotes_verse",
        ),
        Index("idx_verse_footnotes_translation", "translation"),
        Index("idx_verse_footnotes_verse", "verse_id"),
        Index(
            "uq_verse_footnotes_location",
            "verse_id",
            "translation",
            "word_index",
            "footnote_label",
            unique=True,
        ),
    )

    footnote_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    translation: Mapped[str] = mapped_column(String(16), nullable=False)
    order_in_translation: Mapped[int] = mapped_column(Integer, nullable=False)
    word_index: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False)
    footnote_label: Mapped[str] = mapped_column(String(8), nullable=False)
    footnote_text: Mapped[Optional[str]] = mapped_column(LONGTEXT)

    verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses", back_populates="verse_footnotes"
    )
    footnote_cross_references: Mapped[list["FootnoteCrossReferences"]] = relationship(
        "FootnoteCrossReferences", back_populates="footnote"
    )


class VerseHeadings(Base):
    __tablename__ = "verse_headings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_verse_headings_start_verse",
        ),
        Index("idx_verse_headings_start_verse", "start_verse_id"),
        Index("idx_verse_headings_translation_order", "translation", "order_index"),
        Index("idx_verse_headings_translation_start", "translation", "start_verse_id"),
        Index(
            "uq_verse_headings_translation_start_level_text",
            "translation",
            "start_verse_id",
            "heading_level",
            "heading_text",
            mysql_length={"heading_text": 255},
            unique=True,
        ),
    )

    verse_heading_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True
    )
    translation: Mapped[str] = mapped_column(String(16), nullable=False)
    start_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    heading_level: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    heading_text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(INTEGER(unsigned=True), nullable=False)

    start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses", back_populates="verse_headings"
    )


class VerseNotes(Base):
    __tablename__ = "verse_notes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_verse_notes_verse",
        ),
        Index("idx_verse_notes_verse", "verse_id"),
    )

    note_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    note_markdown: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    )

    verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses", back_populates="verse_notes"
    )


class VerseTexts(Base):
    __tablename__ = "verse_texts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_verse_texts_verse",
        ),
        Index("idx_verse_texts_verse", "verse_id"),
        Index(
            "uq_verse_texts_translation_verse", "translation", "verse_id", unique=True
        ),
    )

    verse_text_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    translation: Mapped[str] = mapped_column(String(16), nullable=False)
    marked_text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    plain_text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)

    verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses", back_populates="verse_texts"
    )


class WidgetPassages(Base):
    __tablename__ = "widget_passages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_widget_passages_end_verse",
        ),
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_widget_passages_start_verse",
        ),
        Index("idx_widget_passages_end_verse", "end_verse_id"),
        Index(
            "uq_widget_passages_translation_range",
            "start_verse_id",
            "end_verse_id",
            "translation",
            unique=True,
        ),
    )

    widget_passage_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True
    )
    start_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    end_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    translation: Mapped[str] = mapped_column(String(16), nullable=False)
    reference_text: Mapped[str] = mapped_column(String(64), nullable=False)
    display_text: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[int] = mapped_column(
        SMALLINT(unsigned=True), nullable=False, server_default=text("'1'")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )

    end_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[end_verse_id],
        back_populates="widget_passages_end_verse",
    )
    start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[start_verse_id],
        back_populates="widget_passages_start_verse",
    )


class FootnoteCrossReferences(Base):
    __tablename__ = "footnote_cross_references"
    __table_args__ = (
        ForeignKeyConstraint(
            ["footnote_id"],
            ["verse_footnotes.footnote_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_footnote_cross_references_footnote",
        ),
        ForeignKeyConstraint(
            ["target_end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_footnote_cross_references_target_end",
        ),
        ForeignKeyConstraint(
            ["target_start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_footnote_cross_references_target_start",
        ),
        Index("idx_footnote_cross_references_footnote", "footnote_id"),
        Index("idx_footnote_cross_references_target_end", "target_end_verse_id"),
        Index("idx_footnote_cross_references_target_start", "target_start_verse_id"),
        Index(
            "uq_footnote_cross_references_target",
            "footnote_id",
            "target_start_verse_id",
            "target_end_verse_id",
            "source_order_number",
            unique=True,
        ),
    )

    footnote_cross_reference_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), primary_key=True
    )
    footnote_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    target_start_verse_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    target_end_verse_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    source_order_number: Mapped[Optional[int]] = mapped_column(Integer)
    reference_note: Mapped[Optional[str]] = mapped_column(String(255))

    footnote: Mapped["VerseFootnotes"] = relationship(
        "VerseFootnotes", back_populates="footnote_cross_references"
    )
    target_end_verse: Mapped[Optional["BibleVerses"]] = relationship(
        "BibleVerses",
        foreign_keys=[target_end_verse_id],
        back_populates="footnote_cross_references_target_end_verse",
    )
    target_start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[target_start_verse_id],
        back_populates="footnote_cross_references_target_start_verse",
    )
