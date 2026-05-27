from datetime import datetime

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class TaskJob(Base):
    __tablename__ = "task_jobs"
    __table_args__ = (UniqueConstraint("request_id", name="uq_task_jobs_request_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(unique=True, index=True)
    status: Mapped[str] = mapped_column(default="queued", index=True)
    job_type: Mapped[str] = mapped_column(index=True)
    input_summary: Mapped[str | None] = mapped_column(Text)
    result_summary: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(default="api", index=True)
    module: Mapped[str | None] = mapped_column(index=True)
    operator: Mapped[str | None] = mapped_column(index=True)
    request_id: Mapped[str | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
