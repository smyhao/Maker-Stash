"""add idempotency records and audit logs

Revision ID: 20260519_0004
Revises: 20260519_0003
Create Date: 2026-05-19 00:10:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0004"
down_revision: str | None = "20260519_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("who", sa.String(), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("module", sa.String(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("before_json", sa.Text(), nullable=True),
        sa.Column("after_json", sa.Text(), nullable=True),
        sa.Column("request_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(op.f("ix_audit_logs_module"), "audit_logs", ["module"], unique=False)
    op.create_index(op.f("ix_audit_logs_request_id"), "audit_logs", ["request_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_source"), "audit_logs", ["source"], unique=False)
    op.create_index(op.f("ix_audit_logs_target_id"), "audit_logs", ["target_id"], unique=False)
    op.create_index(op.f("ix_audit_logs_target_type"), "audit_logs", ["target_type"], unique=False)
    op.create_index(op.f("ix_audit_logs_who"), "audit_logs", ["who"], unique=False)

    op.create_table(
        "idempotency_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("module", sa.String(), nullable=True),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_idempotency_request_id"),
    )
    op.create_index(op.f("ix_idempotency_records_action"), "idempotency_records", ["action"], unique=False)
    op.create_index(op.f("ix_idempotency_records_module"), "idempotency_records", ["module"], unique=False)
    op.create_index(op.f("ix_idempotency_records_operator"), "idempotency_records", ["operator"], unique=False)
    op.create_index(op.f("ix_idempotency_records_request_id"), "idempotency_records", ["request_id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_source"), "idempotency_records", ["source"], unique=False)
    op.create_index(op.f("ix_idempotency_records_target_id"), "idempotency_records", ["target_id"], unique=False)
    op.create_index(op.f("ix_idempotency_records_target_type"), "idempotency_records", ["target_type"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_idempotency_records_target_type"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_target_id"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_source"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_request_id"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_operator"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_module"), table_name="idempotency_records")
    op.drop_index(op.f("ix_idempotency_records_action"), table_name="idempotency_records")
    op.drop_table("idempotency_records")
    op.drop_index(op.f("ix_audit_logs_who"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_target_type"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_target_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_source"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_request_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_module"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
