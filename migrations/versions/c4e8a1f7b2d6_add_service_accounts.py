"""Separate human sessions from service bearer tokens."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "c4e8a1f7b2d6"
down_revision: Union[str, Sequence[str], None] = "8a2d1c4e6f70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "api_users",
        sa.Column(
            "account_type",
            sa.Enum("human", "service", name="apiusersaccounttype"),
            nullable=False,
            server_default="human",
        ),
    )
    op.alter_column(
        "api_users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_api_users_account_type_auth",
        "api_users",
        "(account_type = 'human' AND password_hash IS NOT NULL) OR "
        "(account_type = 'service' AND password_hash IS NULL AND is_staff = 0)",
    )
    op.alter_column(
        "api_access_tokens",
        "expires_at",
        existing_type=mysql.TIMESTAMP(),
        nullable=True,
    )
    op.execute(
        sa.text(
            "UPDATE api_access_tokens "
            "SET revoked_at = CURRENT_TIMESTAMP "
            "WHERE revoked_at IS NULL"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM api_users "
            "WHERE account_type = 'service'"
        )
    )
    op.drop_constraint(
        "ck_api_users_account_type_auth",
        "api_users",
        type_="check",
    )
    op.alter_column(
        "api_users",
        "password_hash",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    op.drop_column("api_users", "account_type")
    op.execute(
        sa.text(
            "UPDATE api_access_tokens "
            "SET expires_at = CURRENT_TIMESTAMP "
            "WHERE expires_at IS NULL"
        )
    )
    op.alter_column(
        "api_access_tokens",
        "expires_at",
        existing_type=mysql.TIMESTAMP(),
        nullable=False,
    )
