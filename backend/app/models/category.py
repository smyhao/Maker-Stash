from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("parent_id", "name", name="uq_category_parent_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    code_prefix: Mapped[str] = mapped_column(index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    sort_order: Mapped[int] = mapped_column(default=0)
    description: Mapped[str | None]
    is_system: Mapped[bool] = mapped_column(default=False)

    parent: Mapped["Category | None"] = relationship(remote_side=[id])
