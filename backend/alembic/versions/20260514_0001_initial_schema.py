"""initial schema

Revision ID: 20260514_0001
Revises:
Create Date: 2026-05-14 23:59:00
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260514_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_api_tokens_enabled"), "api_tokens", ["enabled"], unique=False)
    op.create_index(op.f("ix_api_tokens_name"), "api_tokens", ["name"], unique=False)

    op.create_table(
        "backups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("backup_id", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("include_uploads", sa.Boolean(), nullable=False),
        sa.Column("note", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_backups_backup_id"), "backups", ["backup_id"], unique=True)
    op.create_index(op.f("ix_backups_status"), "backups", ["status"], unique=False)

    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("code_prefix", sa.String(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "name", name="uq_category_parent_name"),
    )
    op.create_index(op.f("ix_categories_code_prefix"), "categories", ["code_prefix"], unique=False)
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=False)
    op.create_index(op.f("ix_categories_slug"), "categories", ["slug"], unique=True)

    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("full_code", sa.String(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["locations.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("parent_id", "code", name="uq_location_parent_code"),
    )
    op.create_index(op.f("ix_locations_code"), "locations", ["code"], unique=False)
    op.create_index(op.f("ix_locations_full_code"), "locations", ["full_code"], unique=True)
    op.create_index(op.f("ix_locations_name"), "locations", ["name"], unique=False)

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=True),
        sa.Column("value_type", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_system_settings_key"), "system_settings", ["key"], unique=True)

    op.create_table(
        "tags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tags_name"), "tags", ["name"], unique=True)
    op.create_index(op.f("ix_tags_slug"), "tags", ["slug"], unique=False)

    op.create_table(
        "attribute_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("field_type", sa.String(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("options_json", sa.String(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category_id", "key", name="uq_attribute_definition_category_key"),
    )
    op.create_index(
        op.f("ix_attribute_definitions_category_id"),
        "attribute_definitions",
        ["category_id"],
        unique=False,
    )

    op.create_table(
        "items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("location_id", sa.Integer(), nullable=True),
        sa.Column("location_text", sa.String(), nullable=True),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("need_restock", sa.Boolean(), nullable=False),
        sa.Column("is_favorite", sa.Boolean(), nullable=False),
        sa.Column("cover_attachment_id", sa.Integer(), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_items_category_id"), "items", ["category_id"], unique=False)
    op.create_index(op.f("ix_items_code"), "items", ["code"], unique=True)
    op.create_index(op.f("ix_items_is_archived"), "items", ["is_archived"], unique=False)
    op.create_index(op.f("ix_items_is_favorite"), "items", ["is_favorite"], unique=False)
    op.create_index(op.f("ix_items_location_id"), "items", ["location_id"], unique=False)
    op.create_index(op.f("ix_items_name"), "items", ["name"], unique=False)
    op.create_index(op.f("ix_items_need_restock"), "items", ["need_restock"], unique=False)
    op.create_index(op.f("ix_items_status"), "items", ["status"], unique=False)

    op.create_table(
        "aliases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "alias", name="uq_item_alias"),
    )
    op.create_index(op.f("ix_aliases_alias"), "aliases", ["alias"], unique=False)
    op.create_index(op.f("ix_aliases_item_id"), "aliases", ["item_id"], unique=False)

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("attachment_type", sa.String(), nullable=False),
        sa.Column("original_name", sa.String(), nullable=False),
        sa.Column("stored_name", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_cover", sa.Boolean(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attachments_attachment_type"), "attachments", ["attachment_type"], unique=False)
    op.create_index(op.f("ix_attachments_is_deleted"), "attachments", ["is_deleted"], unique=False)
    op.create_index(op.f("ix_attachments_item_id"), "attachments", ["item_id"], unique=False)

    op.create_table(
        "identifiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type", "value", name="uq_identifier_type_value"),
    )
    op.create_index(op.f("ix_identifiers_item_id"), "identifiers", ["item_id"], unique=False)
    op.create_index(op.f("ix_identifiers_value"), "identifiers", ["value"], unique=False)

    op.create_table(
        "item_attribute_values",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("attribute_definition_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=True),
        sa.Column("value_type", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["attribute_definition_id"], ["attribute_definitions.id"]),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("item_id", "key", name="uq_item_attribute_key"),
    )
    op.create_index(
        op.f("ix_item_attribute_values_item_id"),
        "item_attribute_values",
        ["item_id"],
        unique=False,
    )

    op.create_table(
        "item_tags",
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("tag_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
        sa.PrimaryKeyConstraint("item_id", "tag_id"),
        sa.UniqueConstraint("item_id", "tag_id", name="uq_item_tag"),
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=True),
        sa.Column("note_type", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("quantity_change", sa.Numeric(12, 3), nullable=True),
        sa.Column("quantity_after", sa.Numeric(12, 3), nullable=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("operator", sa.String(), nullable=True),
        sa.Column("metadata_json", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["item_id"], ["items.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_notes_item_id"), "notes", ["item_id"], unique=False)
    op.create_index(op.f("ix_notes_note_type"), "notes", ["note_type"], unique=False)
    op.create_index(op.f("ix_notes_source"), "notes", ["source"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_notes_source"), table_name="notes")
    op.drop_index(op.f("ix_notes_note_type"), table_name="notes")
    op.drop_index(op.f("ix_notes_item_id"), table_name="notes")
    op.drop_table("notes")
    op.drop_table("item_tags")
    op.drop_index(op.f("ix_item_attribute_values_item_id"), table_name="item_attribute_values")
    op.drop_table("item_attribute_values")
    op.drop_index(op.f("ix_identifiers_value"), table_name="identifiers")
    op.drop_index(op.f("ix_identifiers_item_id"), table_name="identifiers")
    op.drop_table("identifiers")
    op.drop_index(op.f("ix_attachments_item_id"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_is_deleted"), table_name="attachments")
    op.drop_index(op.f("ix_attachments_attachment_type"), table_name="attachments")
    op.drop_table("attachments")
    op.drop_index(op.f("ix_aliases_item_id"), table_name="aliases")
    op.drop_index(op.f("ix_aliases_alias"), table_name="aliases")
    op.drop_table("aliases")
    op.drop_index(op.f("ix_items_status"), table_name="items")
    op.drop_index(op.f("ix_items_need_restock"), table_name="items")
    op.drop_index(op.f("ix_items_name"), table_name="items")
    op.drop_index(op.f("ix_items_location_id"), table_name="items")
    op.drop_index(op.f("ix_items_is_favorite"), table_name="items")
    op.drop_index(op.f("ix_items_is_archived"), table_name="items")
    op.drop_index(op.f("ix_items_code"), table_name="items")
    op.drop_index(op.f("ix_items_category_id"), table_name="items")
    op.drop_table("items")
    op.drop_index(op.f("ix_attribute_definitions_category_id"), table_name="attribute_definitions")
    op.drop_table("attribute_definitions")
    op.drop_index(op.f("ix_tags_slug"), table_name="tags")
    op.drop_index(op.f("ix_tags_name"), table_name="tags")
    op.drop_table("tags")
    op.drop_index(op.f("ix_system_settings_key"), table_name="system_settings")
    op.drop_table("system_settings")
    op.drop_index(op.f("ix_locations_name"), table_name="locations")
    op.drop_index(op.f("ix_locations_full_code"), table_name="locations")
    op.drop_index(op.f("ix_locations_code"), table_name="locations")
    op.drop_table("locations")
    op.drop_index(op.f("ix_categories_slug"), table_name="categories")
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_code_prefix"), table_name="categories")
    op.drop_table("categories")
    op.drop_index(op.f("ix_backups_status"), table_name="backups")
    op.drop_index(op.f("ix_backups_backup_id"), table_name="backups")
    op.drop_table("backups")
    op.drop_index(op.f("ix_api_tokens_name"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_enabled"), table_name="api_tokens")
    op.drop_table("api_tokens")
