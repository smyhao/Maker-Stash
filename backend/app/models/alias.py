from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class Alias(Base):
    __tablename__ = "aliases"
    __table_args__ = (UniqueConstraint("item_id", "alias", name="uq_item_alias"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    alias: Mapped[str] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
