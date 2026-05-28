"""add visual storage container metadata

Revision ID: 20260527_0008
Revises: 20260522_0007
Create Date: 2026-05-27 10:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260527_0008"
down_revision: str | None = "20260522_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("layout_type", sa.String(), nullable=True))
    op.add_column("locations", sa.Column("layout_rows", sa.Integer(), nullable=True))
    op.add_column("locations", sa.Column("layout_columns", sa.Integer(), nullable=True))
    op.add_column("locations", sa.Column("appearance_color", sa.String(), nullable=True))
    op.add_column("locations", sa.Column("appearance_icon", sa.String(), nullable=True))
    op.add_column("locations", sa.Column("is_slot", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("locations", sa.Column("slot_key", sa.String(), nullable=True))
    op.add_column("locations", sa.Column("slot_order", sa.Integer(), nullable=True))
    op.create_index("ix_locations_is_slot", "locations", ["is_slot"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_locations_is_slot", table_name="locations")
    op.drop_column("locations", "slot_order")
    op.drop_column("locations", "slot_key")
    op.drop_column("locations", "is_slot")
    op.drop_column("locations", "appearance_icon")
    op.drop_column("locations", "appearance_color")
    op.drop_column("locations", "layout_columns")
    op.drop_column("locations", "layout_rows")
    op.drop_column("locations", "layout_type")
