from sqlalchemy import Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Location(TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (UniqueConstraint("parent_id", "code", name="uq_location_parent_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    code: Mapped[str] = mapped_column(index=True)
    full_code: Mapped[str] = mapped_column(unique=True, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"))
    type: Mapped[str | None]
    description: Mapped[str | None]
    sort_order: Mapped[int] = mapped_column(default=0)
    layout_type: Mapped[str | None]
    layout_rows: Mapped[int | None]
    layout_columns: Mapped[int | None]
    appearance_color: Mapped[str | None]
    appearance_icon: Mapped[str | None]
    is_slot: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    slot_key: Mapped[str | None]
    slot_order: Mapped[int | None]

    parent: Mapped["Location | None"] = relationship(remote_side=[id])
