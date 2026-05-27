"""add workflow plans

Revision ID: 20260519_0006
Revises: 20260519_0005
Create Date: 2026-05-19 00:30:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0006"
down_revision: str | None = "20260519_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflow_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.String(), nullable=False),
        sa.Column("workflow_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("plan_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("confirm_token", sa.String(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("module", sa.String(), nullable=True),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_workflow_plans_request_id"),
    )
    op.create_index(op.f("ix_workflow_plans_confirm_token"), "workflow_plans", ["confirm_token"], unique=False)
    op.create_index(op.f("ix_workflow_plans_module"), "workflow_plans", ["module"], unique=False)
    op.create_index(op.f("ix_workflow_plans_operator"), "workflow_plans", ["operator"], unique=False)
    op.create_index(op.f("ix_workflow_plans_plan_id"), "workflow_plans", ["plan_id"], unique=True)
    op.create_index(op.f("ix_workflow_plans_request_id"), "workflow_plans", ["request_id"], unique=False)
    op.create_index(op.f("ix_workflow_plans_source"), "workflow_plans", ["source"], unique=False)
    op.create_index(op.f("ix_workflow_plans_status"), "workflow_plans", ["status"], unique=False)
    op.create_index(op.f("ix_workflow_plans_task_id"), "workflow_plans", ["task_id"], unique=False)
    op.create_index(op.f("ix_workflow_plans_workflow_type"), "workflow_plans", ["workflow_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_workflow_plans_workflow_type"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_task_id"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_status"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_source"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_request_id"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_plan_id"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_operator"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_module"), table_name="workflow_plans")
    op.drop_index(op.f("ix_workflow_plans_confirm_token"), table_name="workflow_plans")
    op.drop_table("workflow_plans")
