from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id"), index=True)
    attachment_type: Mapped[str] = mapped_column(index=True)
    original_name: Mapped[str]
    stored_name: Mapped[str]
    file_path: Mapped[str]
    thumbnail_path: Mapped[str | None]
    mime_type: Mapped[str | None]
    size_bytes: Mapped[int | None]
    description: Mapped[str | None]
    is_cover: Mapped[bool] = mapped_column(default=False)
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
