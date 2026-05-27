"""add attachment thumbnail path

Revision ID: 20260516_0002
Revises: 20260514_0001
Create Date: 2026-05-16 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0002"
down_revision: str | None = "20260514_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("attachments")}
    if "thumbnail_path" not in columns:
        op.add_column("attachments", sa.Column("thumbnail_path", sa.String(), nullable=True))


def downgrade() -> None:
    # The current initial migration already includes this column, so downgrading
    # this compatibility migration should leave the 0001 schema intact.
    return
