from datetime import datetime

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    who: Mapped[str | None] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(index=True)
    module: Mapped[str | None] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(index=True)
    target_type: Mapped[str] = mapped_column(index=True)
    target_id: Mapped[str] = mapped_column(index=True)
    before_json: Mapped[str | None] = mapped_column(Text)
    after_json: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[str | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (UniqueConstraint("request_id", name="uq_idempotency_request_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[str] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(index=True)
    target_type: Mapped[str] = mapped_column(index=True)
    target_id: Mapped[str] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(index=True)
    module: Mapped[str | None] = mapped_column(index=True)
    operator: Mapped[str | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
