"""add sermon user ownership

Revision ID: 5a4f1f2d8c9b
Revises: 3c7f2b8a9d10
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "5a4f1f2d8c9b"
down_revision: Union[str, Sequence[str], None] = "3c7f2b8a9d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    bryce_id = bind.scalar(
        sa.text("select user_id from api_users where username = :username"),
        {"username": "bryce"},
    )
    if bryce_id is None:
        raise RuntimeError(
            "Cannot add sermon ownership: api_users.username='bryce' was not found."
        )

    op.add_column(
        "sermons",
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=True),
    )
    op.execute(
        sa.text("update sermons set user_id = :user_id where user_id is null").bindparams(
            user_id=bryce_id
        )
    )
    op.alter_column(
        "sermons",
        "user_id",
        existing_type=mysql.BIGINT(unsigned=True),
        nullable=False,
    )
    op.create_index("idx_sermons_user_id", "sermons", ["user_id"], unique=False)
    op.create_foreign_key(
        "fk_sermons_user",
        "sermons",
        "api_users",
        ["user_id"],
        ["user_id"],
        onupdate="CASCADE",
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_sermons_user", "sermons", type_="foreignkey")
    op.drop_index("idx_sermons_user_id", table_name="sermons")
    op.drop_column("sermons", "user_id")
