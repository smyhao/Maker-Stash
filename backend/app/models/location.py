from sqlalchemy import ForeignKey, UniqueConstraint
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

    parent: Mapped["Location | None"] = relationship(remote_side=[id])
