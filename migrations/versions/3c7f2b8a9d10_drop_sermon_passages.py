"""drop sermon passages

Revision ID: 3c7f2b8a9d10
Revises: 997d40992dc7
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "3c7f2b8a9d10"
down_revision: Union[str, Sequence[str], None] = "997d40992dc7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("sermon_passages")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "sermon_passages",
        sa.Column(
            "sermon_passage_id",
            mysql.BIGINT(unsigned=True),
            nullable=False,
        ),
        sa.Column("sermon_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("start_verse_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("end_verse_id", mysql.BIGINT(unsigned=True), nullable=True),
        sa.Column("reference_text", sa.String(length=64), nullable=True),
        sa.Column("context_note", sa.String(length=512), nullable=True),
        sa.Column(
            "display_order",
            mysql.SMALLINT(unsigned=True),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["end_verse_id"],
            ["bible_verses.verse_id"],
            name="fk_sermon_passages_end_verse",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["sermon_id"],
            ["sermons.sermon_id"],
            name="fk_sermon_passages_sermon",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["start_verse_id"],
            ["bible_verses.verse_id"],
            name="fk_sermon_passages_start_verse",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("sermon_passage_id"),
    )
    op.create_index(
        "idx_sermon_passages_end_verse",
        "sermon_passages",
        ["end_verse_id"],
        unique=False,
    )
    op.create_index(
        "idx_sermon_passages_start_verse",
        "sermon_passages",
        ["start_verse_id"],
        unique=False,
    )
    op.create_index(
        "uq_sermon_passages_sermon_display_order",
        "sermon_passages",
        ["sermon_id", "display_order"],
        unique=True,
    )
