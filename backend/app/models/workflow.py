from datetime import datetime

from sqlalchemy import Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import utcnow


class WorkflowPlan(Base):
    __tablename__ = "workflow_plans"
    __table_args__ = (UniqueConstraint("request_id", name="uq_workflow_plans_request_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[str] = mapped_column(unique=True, index=True)
    workflow_type: Mapped[str] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(default="planned", index=True)
    plan_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text)
    confirm_token: Mapped[str] = mapped_column(index=True)
    task_id: Mapped[str | None] = mapped_column(index=True)
    source: Mapped[str] = mapped_column(default="api", index=True)
    module: Mapped[str | None] = mapped_column(index=True)
    operator: Mapped[str | None] = mapped_column(index=True)
    request_id: Mapped[str | None] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    confirmed_at: Mapped[datetime | None]
