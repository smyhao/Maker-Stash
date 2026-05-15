from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class Backup(Base):
    __tablename__ = "backups"

    id: Mapped[int] = mapped_column(primary_key=True)
    backup_id: Mapped[str] = mapped_column(unique=True, index=True)
    file_path: Mapped[str]
    size_bytes: Mapped[int | None]
    include_uploads: Mapped[bool] = mapped_column(default=True)
    note: Mapped[str | None]
    status: Mapped[str] = mapped_column(default="success", index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
