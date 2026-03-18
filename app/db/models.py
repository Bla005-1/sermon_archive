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
        Index("idx_bible_books_order", "order_num"),
        Index("uq_bible_books_name", "name", unique=True),
        Index("ux_bible_books_name", "name", unique=True),
    )

    book_id: Mapped[int] = mapped_column(TINYINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    order_num: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
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
    __table_args__ = (Index("uq_church_fathers_name", "name", unique=True),)

    father_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    default_year: Mapped[Optional[int]] = mapped_column(Integer)
    wiki_url: Mapped[Optional[str]] = mapped_column(String(512))

    commentaries: Mapped[list["Commentaries"]] = relationship(
        "Commentaries", back_populates="father"
    )


class Sermons(Base):
    __tablename__ = "sermons"
    __table_args__ = (
        Index("idx_sermons_preached_on", "preached_on"),
        Index("idx_sermons_speaker_date", "speaker_name", "preached_on"),
        Index("ix_sermons_preached_on", "preached_on"),
        Index("ix_sermons_speaker", "speaker_name"),
    )

    sermon_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    preached_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    speaker_name: Mapped[Optional[str]] = mapped_column(String(128))
    series_name: Mapped[Optional[str]] = mapped_column(String(128))
    location_name: Mapped[Optional[str]] = mapped_column(String(128))
    notes_md: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    )

    attachments: Mapped[list["Attachments"]] = relationship(
        "Attachments", back_populates="sermon"
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
            name="fk_api_tokens_user",
        ),
        Index("ix_api_access_tokens_expires", "expires_at"),
        Index("ix_api_access_tokens_user", "user_id"),
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
        Index("ix_api_sessions_expires", "expires_at"),
        Index("ix_api_sessions_user", "user_id"),
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


class Attachments(Base):
    __tablename__ = "attachments"
    __table_args__ = (
        ForeignKeyConstraint(
            ["sermon_id"],
            ["sermons.sermon_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_att_sermon",
        ),
        Index("idx_attachments_created", "created_at"),
        Index("idx_attachments_sermon", "sermon_id"),
        Index("ix_attachments_rel_path", "rel_path"),
        Index("ix_attachments_sermon", "sermon_id"),
    )

    attachment_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    sermon_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    rel_path: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(255))
    byte_size: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )

    sermon: Mapped["Sermons"] = relationship("Sermons", back_populates="attachments")


class BibleVerses(Base):
    __tablename__ = "bible_verses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["book_id"],
            ["bible_books.book_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_bv_book",
        ),
        Index("idx_bible_verses_book_ch", "book_id", "chapter"),
        Index("ix_bible_verses_book_ch", "book_id", "chapter"),
        Index("uq_bible_verses_loc", "book_id", "chapter", "verse", unique=True),
        Index("ux_bible_verses_canonical", "book_id", "chapter", "verse", unique=True),
    )

    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    book_id: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    chapter: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False)
    verse: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False)
    weight: Mapped[float] = mapped_column(
        Float, nullable=False, server_default=text("'1'")
    )

    book: Mapped["BibleBooks"] = relationship(
        "BibleBooks", back_populates="bible_verses"
    )
    bible_widget_verses_end_verse: Mapped[list["BibleWidgetVerses"]] = relationship(
        "BibleWidgetVerses",
        foreign_keys="[BibleWidgetVerses.end_verse_id]",
        back_populates="end_verse",
    )
    bible_widget_verses_start_verse: Mapped[list["BibleWidgetVerses"]] = relationship(
        "BibleWidgetVerses",
        foreign_keys="[BibleWidgetVerses.start_verse_id]",
        back_populates="start_verse",
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
    footnote_cross_refs_to_end_verse: Mapped[list["FootnoteCrossRefs"]] = relationship(
        "FootnoteCrossRefs",
        foreign_keys="[FootnoteCrossRefs.to_end_verse_id]",
        back_populates="to_end_verse",
    )
    footnote_cross_refs_to_start_verse: Mapped[list["FootnoteCrossRefs"]] = (
        relationship(
            "FootnoteCrossRefs",
            foreign_keys="[FootnoteCrossRefs.to_start_verse_id]",
            back_populates="to_start_verse",
        )
    )
    footnotes: Mapped[list["Footnotes"]] = relationship(
        "Footnotes", back_populates="verse"
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
    verse_crossrefs_from_verse: Mapped[list["VerseCrossrefs"]] = relationship(
        "VerseCrossrefs",
        foreign_keys="[VerseCrossrefs.from_verse_id]",
        back_populates="from_verse",
    )
    verse_crossrefs_to_end_verse: Mapped[list["VerseCrossrefs"]] = relationship(
        "VerseCrossrefs",
        foreign_keys="[VerseCrossrefs.to_end_verse_id]",
        back_populates="to_end_verse",
    )
    verse_crossrefs_to_start_verse: Mapped[list["VerseCrossrefs"]] = relationship(
        "VerseCrossrefs",
        foreign_keys="[VerseCrossrefs.to_start_verse_id]",
        back_populates="to_start_verse",
    )
    verse_headings: Mapped[list["VerseHeadings"]] = relationship(
        "VerseHeadings", back_populates="start_verse"
    )
    verse_notes: Mapped[list["VerseNotes"]] = relationship(
        "VerseNotes", back_populates="verse"
    )
    verse_texts_marked: Mapped[list["VerseTextsMarked"]] = relationship(
        "VerseTextsMarked", back_populates="verse"
    )


class BibleWidgetVerses(Base):
    __tablename__ = "bible_widget_verses"
    __table_args__ = (
        ForeignKeyConstraint(
            ["end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_widget_end_verse",
        ),
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_widget_start_verse",
        ),
        Index("fk_widget_end_verse", "end_verse_id"),
        Index(
            "uq_widget_passage_tr",
            "start_verse_id",
            "end_verse_id",
            "translation",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    start_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    end_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    translation: Mapped[str] = mapped_column(String(16), nullable=False)
    ref: Mapped[str] = mapped_column(String(64), nullable=False)
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
        back_populates="bible_widget_verses_end_verse",
    )
    start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[start_verse_id],
        back_populates="bible_widget_verses_start_verse",
    )


class Commentaries(Base):
    __tablename__ = "commentaries"
    __table_args__ = (
        ForeignKeyConstraint(
            ["book_id"],
            ["bible_books.book_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="commentaries_ibfk_2",
        ),
        ForeignKeyConstraint(
            ["end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="commentaries_ibfk_4",
        ),
        ForeignKeyConstraint(
            ["father_id"],
            ["church_fathers.father_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="commentaries_ibfk_1",
        ),
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="commentaries_ibfk_3",
        ),
        Index("book_id", "book_id"),
        Index("end_verse_id", "end_verse_id"),
        Index("father_id", "father_id"),
        Index("start_verse_id", "start_verse_id"),
    )

    commentary_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    father_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    book_id: Mapped[int] = mapped_column(TINYINT(unsigned=True), nullable=False)
    start_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    end_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    txt: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
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


class FootnoteCrossRefs(Base):
    __tablename__ = "footnote_cross_refs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["to_end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="footnote_cross_refs_ibfk_2",
        ),
        ForeignKeyConstraint(
            ["to_start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="footnote_cross_refs_ibfk_1",
        ),
        Index("idx_crossref_footnote", "footnote_id"),
        Index("idx_crossref_target_end", "to_end_verse_id"),
        Index("idx_crossref_target_start", "to_start_verse_id"),
        Index(
            "uq_cross",
            "footnote_id",
            "to_start_verse_id",
            "to_end_verse_id",
            "source_order_number",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    footnote_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    to_start_verse_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), nullable=False
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP, nullable=False, server_default=text("CURRENT_TIMESTAMP")
    )
    to_end_verse_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    source_order_number: Mapped[Optional[int]] = mapped_column(Integer)
    reference_note: Mapped[Optional[str]] = mapped_column(String(255))

    to_end_verse: Mapped[Optional["BibleVerses"]] = relationship(
        "BibleVerses",
        foreign_keys=[to_end_verse_id],
        back_populates="footnote_cross_refs_to_end_verse",
    )
    to_start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[to_start_verse_id],
        back_populates="footnote_cross_refs_to_start_verse",
    )


class Footnotes(Base):
    __tablename__ = "footnotes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="footnotes_ibfk_1",
        ),
        Index("idx_footnotes_translation", "translation"),
        Index("idx_footnotes_verse", "verse_id"),
        Index(
            "uq_footnote_location",
            "verse_id",
            "translation",
            "word_index",
            "footnote_label",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    translation: Mapped[str] = mapped_column(String(16), nullable=False)
    order_in_translation: Mapped[int] = mapped_column(Integer, nullable=False)
    word_index: Mapped[int] = mapped_column(SMALLINT(unsigned=True), nullable=False)
    footnote_label: Mapped[str] = mapped_column(String(8), nullable=False)
    footnote_text: Mapped[Optional[str]] = mapped_column(LONGTEXT)

    verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses", back_populates="footnotes"
    )


class SermonPassages(Base):
    __tablename__ = "sermon_passages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_sp_end",
        ),
        ForeignKeyConstraint(
            ["sermon_id"],
            ["sermons.sermon_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_sp_sermon",
        ),
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="RESTRICT",
            onupdate="CASCADE",
            name="fk_sp_start",
        ),
        Index("idx_sermon_passages_end", "end_verse_id"),
        Index("idx_sermon_passages_start", "start_verse_id"),
        Index("ix_sp_end", "end_verse_id"),
        Index("ix_sp_ord", "ord"),
        Index("ix_sp_sermon", "sermon_id"),
        Index("ix_sp_start", "start_verse_id"),
        Index("uq_sermon_ord", "sermon_id", "ord", unique=True),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    sermon_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    start_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    end_verse_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    ref_text: Mapped[Optional[str]] = mapped_column(String(64))
    context_note: Mapped[Optional[str]] = mapped_column(String(512))
    ord: Mapped[Optional[int]] = mapped_column(
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


class VerseCrossrefs(Base):
    __tablename__ = "verse_crossrefs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["from_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="verse_crossrefs_ibfk_1",
        ),
        ForeignKeyConstraint(
            ["to_end_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="verse_crossrefs_ibfk_3",
        ),
        ForeignKeyConstraint(
            ["to_start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="verse_crossrefs_ibfk_2",
        ),
        Index("to_end_verse_id", "to_end_verse_id"),
        Index("to_start_verse_id", "to_start_verse_id"),
        Index(
            "uq_cross",
            "from_verse_id",
            "to_start_verse_id",
            "to_end_verse_id",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    from_verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    to_start_verse_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True), nullable=False
    )
    to_end_verse_id: Mapped[Optional[int]] = mapped_column(BIGINT(unsigned=True))
    votes: Mapped[Optional[int]] = mapped_column(Integer)
    note: Mapped[Optional[str]] = mapped_column(String(255))

    from_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[from_verse_id],
        back_populates="verse_crossrefs_from_verse",
    )
    to_end_verse: Mapped[Optional["BibleVerses"]] = relationship(
        "BibleVerses",
        foreign_keys=[to_end_verse_id],
        back_populates="verse_crossrefs_to_end_verse",
    )
    to_start_verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses",
        foreign_keys=[to_start_verse_id],
        back_populates="verse_crossrefs_to_start_verse",
    )


class VerseHeadings(Base):
    __tablename__ = "verse_headings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="fk_vsh_start_verse",
        ),
        Index("idx_start_verse_id", "start_verse_id"),
        Index("idx_translation_order", "translation", "order_index"),
        Index("idx_translation_start", "translation", "start_verse_id"),
        Index(
            "translation",
            "translation",
            "start_verse_id",
            "heading_level",
            "heading_text",
            mysql_length={"heading_text": 255},
            unique=True,
        ),
    )

    section_heading_id: Mapped[int] = mapped_column(
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
            name="fk_vn_verse",
        ),
        Index("idx_verse_notes_verse", "verse_id"),
        Index("ix_verse_notes_verse", "verse_id"),
    )

    note_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    note_md: Mapped[Optional[str]] = mapped_column(LONGTEXT)
    created_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        TIMESTAMP, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
    )

    verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses", back_populates="verse_notes"
    )


class VerseTextsMarked(Base):
    __tablename__ = "verse_texts_marked"
    __table_args__ = (
        ForeignKeyConstraint(
            ["verse_id"],
            ["bible_verses.verse_id"],
            ondelete="CASCADE",
            onupdate="CASCADE",
            name="verse_texts_marked_ibfk_1",
        ),
        Index("uq_translation_verse", "translation", "verse_id", unique=True),
        Index("verse_id", "verse_id"),
    )

    verse_text_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True)
    verse_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), nullable=False)
    translation: Mapped[str] = mapped_column(String(16), nullable=False)
    marked_text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)
    plain_text: Mapped[str] = mapped_column(LONGTEXT, nullable=False)

    verse: Mapped["BibleVerses"] = relationship(
        "BibleVerses", back_populates="verse_texts_marked"
    )
