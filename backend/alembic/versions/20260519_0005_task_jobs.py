"""add lightweight task jobs

Revision ID: 20260519_0005
Revises: 20260519_0004
Create Date: 2026-05-19 00:20:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0005"
down_revision: str | None = "20260519_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("task_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("module", sa.String(), nullable=True),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_task_jobs_request_id"),
    )
    op.create_index(op.f("ix_task_jobs_job_type"), "task_jobs", ["job_type"], unique=False)
    op.create_index(op.f("ix_task_jobs_module"), "task_jobs", ["module"], unique=False)
    op.create_index(op.f("ix_task_jobs_operator"), "task_jobs", ["operator"], unique=False)
    op.create_index(op.f("ix_task_jobs_request_id"), "task_jobs", ["request_id"], unique=False)
    op.create_index(op.f("ix_task_jobs_source"), "task_jobs", ["source"], unique=False)
    op.create_index(op.f("ix_task_jobs_status"), "task_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_task_jobs_task_id"), "task_jobs", ["task_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_task_jobs_task_id"), table_name="task_jobs")
    op.drop_index(op.f("ix_task_jobs_status"), table_name="task_jobs")
    op.drop_index(op.f("ix_task_jobs_source"), table_name="task_jobs")
    op.drop_index(op.f("ix_task_jobs_request_id"), table_name="task_jobs")
    op.drop_index(op.f("ix_task_jobs_operator"), table_name="task_jobs")
    op.drop_index(op.f("ix_task_jobs_module"), table_name="task_jobs")
    op.drop_index(op.f("ix_task_jobs_job_type"), table_name="task_jobs")
    op.drop_table("task_jobs")
