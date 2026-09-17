"""deadline status

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "deadlines",
        sa.Column("status", sa.String(), nullable=False, server_default="not_started"),
    )


def downgrade() -> None:
    op.drop_column("deadlines", "status")
