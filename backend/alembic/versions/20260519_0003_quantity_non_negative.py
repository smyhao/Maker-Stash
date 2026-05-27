"""add non-negative quantity constraint

Revision ID: 20260519_0003
Revises: 20260516_0002
Create Date: 2026-05-19 00:00:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0003"
down_revision: str | None = "20260516_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("PRAGMA foreign_keys=OFF")
        op.execute("DROP TABLE IF EXISTS _alembic_tmp_items")
    op.execute(
        sa.text(
            """
            INSERT INTO notes (item_id, note_type, content, source, created_at)
            SELECT
                id,
                'system',
                '迁移修正负库存：原数量 ' || quantity || '，已置为 0 以满足非负库存约束',
                'migration',
                CURRENT_TIMESTAMP
            FROM items
            WHERE quantity < 0
            """
        )
    )
    op.execute(sa.text("UPDATE items SET quantity = 0 WHERE quantity < 0"))
    with op.batch_alter_table("items") as batch_op:
        batch_op.create_check_constraint(
            "ck_items_quantity_non_negative",
            "quantity IS NULL OR quantity >= 0",
        )
    if bind.dialect.name == "sqlite":
        op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    with op.batch_alter_table("items") as batch_op:
        batch_op.drop_constraint("ck_items_quantity_non_negative", type_="check")
