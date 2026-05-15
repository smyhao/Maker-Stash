from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ApiToken(TimestampMixin, Base):
    __tablename__ = "api_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(index=True)
    token_hash: Mapped[str]
    enabled: Mapped[bool] = mapped_column(default=True, index=True)
    description: Mapped[str | None]
    last_used_at: Mapped[datetime | None]
