from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Item(TimestampMixin, Base):
    __tablename__ = "items"
    __table_args__ = (
        CheckConstraint("quantity IS NULL OR quantity >= 0", name="ck_items_quantity_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True, index=True)
    name: Mapped[str] = mapped_column(index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    location_text: Mapped[str | None]
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    unit: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="normal", index=True)
    description: Mapped[str | None]
    need_restock: Mapped[bool] = mapped_column(default=False, index=True)
    is_favorite: Mapped[bool] = mapped_column(default=False, index=True)
    cover_attachment_id: Mapped[int | None]
    is_archived: Mapped[bool] = mapped_column(default=False, index=True)

    category = relationship("Category")
    location = relationship("Location")
