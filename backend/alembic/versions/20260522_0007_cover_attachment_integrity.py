"""clean stale cover attachment references

Revision ID: 20260522_0007
Revises: 20260519_0006
Create Date: 2026-05-22 21:20:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260522_0007"
down_revision: str | None = "20260519_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE attachments SET is_cover = 0 WHERE is_deleted = 1"))
    op.execute(
        sa.text(
            """
            UPDATE items
            SET cover_attachment_id = NULL
            WHERE cover_attachment_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM attachments
                WHERE attachments.id = items.cover_attachment_id
                  AND attachments.item_id = items.id
                  AND attachments.is_deleted = 0
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE attachments
            SET is_cover = 0
            WHERE is_cover = 1
              AND NOT EXISTS (
                SELECT 1
                FROM items
                WHERE items.id = attachments.item_id
                  AND items.cover_attachment_id = attachments.id
              )
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE attachments
            SET is_cover = 1
            WHERE is_deleted = 0
              AND EXISTS (
                SELECT 1
                FROM items
                WHERE items.id = attachments.item_id
                  AND items.cover_attachment_id = attachments.id
              )
            """
        )
    )


def downgrade() -> None:
    pass
