from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AttributeDefinition(TimestampMixin, Base):
    __tablename__ = "attribute_definitions"
    __table_args__ = (
        UniqueConstraint("category_id", "key", name="uq_attribute_definition_category_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    name: Mapped[str]
    key: Mapped[str]
    field_type: Mapped[str]
    unit: Mapped[str | None]
    options_json: Mapped[str | None]
    required: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)
    is_enabled: Mapped[bool] = mapped_column(default=True)


class ItemAttributeValue(TimestampMixin, Base):
    __tablename__ = "item_attribute_values"
    __table_args__ = (UniqueConstraint("item_id", "key", name="uq_item_attribute_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    attribute_definition_id: Mapped[int | None] = mapped_column(
        ForeignKey("attribute_definitions.id")
    )
    name: Mapped[str]
    key: Mapped[str]
    value: Mapped[str | None]
    value_type: Mapped[str | None]
    unit: Mapped[str | None]
    sort_order: Mapped[int] = mapped_column(default=0)
