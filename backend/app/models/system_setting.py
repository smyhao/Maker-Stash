from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(unique=True, index=True)
    value: Mapped[str | None]
    value_type: Mapped[str] = mapped_column(default="text")
    description: Mapped[str | None]
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
