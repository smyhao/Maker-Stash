from datetime import datetime

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class Identifier(Base):
    __tablename__ = "identifiers"
    __table_args__ = (UniqueConstraint("type", "value", name="uq_identifier_type_value"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    type: Mapped[str]
    value: Mapped[str] = mapped_column(index=True)
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
