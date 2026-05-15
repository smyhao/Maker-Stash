from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id"), index=True)
    note_type: Mapped[str] = mapped_column(index=True)
    content: Mapped[str]
    quantity_change: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    quantity_after: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    source: Mapped[str] = mapped_column(default="api", index=True)
    operator: Mapped[str | None]
    metadata_json: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
