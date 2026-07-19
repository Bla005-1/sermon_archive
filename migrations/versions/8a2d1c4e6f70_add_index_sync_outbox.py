"""Add durable sermon index synchronization outbox."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "8a2d1c4e6f70"
down_revision: Union[str, Sequence[str], None] = "5a4f1f2d8c9b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "index_sync_outbox",
        sa.Column("event_id", mysql.BIGINT(unsigned=True), primary_key=True, autoincrement=True),
        sa.Column("sermon_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("operation", sa.Enum("upsert", "delete", name="indexsyncoperation"), nullable=False),
        sa.Column("status", sa.Enum("pending", "processing", "delivered", "failed", name="indexsyncstatus"), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("next_attempt_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
    )
    op.create_index("idx_index_sync_outbox_dispatch", "index_sync_outbox", ["status", "next_attempt_at", "event_id"])
    op.create_index("idx_index_sync_outbox_sermon", "index_sync_outbox", ["sermon_id", "event_id"])


def downgrade() -> None:
    op.drop_table("index_sync_outbox")
