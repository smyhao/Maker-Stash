from __future__ import annotations

from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.mixins import utcnow
from app.models.task import TaskJob
from app.schemas.task import TaskCreate
from app.services.audit_service import WriteContext


TASK_STATUSES = {"queued", "running", "succeeded", "failed"}


class TaskService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def submit(self, payload: TaskCreate, *, commit: bool = True) -> TaskJob:
        ctx = WriteContext.from_payload(payload)
        if ctx.request_id:
            existing = self.db.scalar(select(TaskJob).where(TaskJob.request_id == ctx.request_id))
            if existing:
                return existing
        job_type = payload.job_type.strip()
        if not job_type:
            raise AppError("VALIDATION_ERROR", "job_type 不能为空")
        task = TaskJob(
            task_id=f"task-{uuid4().hex}",
            status="queued",
            job_type=job_type,
            input_summary=payload.input_summary,
            source=ctx.source,
            module=ctx.module,
            operator=ctx.operator,
            request_id=ctx.request_id,
        )
        self.db.add(task)
        self._finish_write(task, commit)
        return task

    def get(self, task_id: str) -> TaskJob:
        task = self.db.scalar(select(TaskJob).where(TaskJob.task_id == task_id))
        if task is None:
            raise NotFoundError("TASK_NOT_FOUND", f"任务不存在：{task_id}")
        return task

    def mark_running(self, task_id: str, *, commit: bool = True) -> TaskJob:
        task = self.get(task_id)
        if task.status != "queued":
            raise AppError("INVALID_TASK_STATE", "只有 queued 任务可以进入 running", status.HTTP_409_CONFLICT)
        task.status = "running"
        task.started_at = utcnow()
        self._finish_write(task, commit)
        return task

    def mark_succeeded(self, task_id: str, result_summary: str | None = None, *, commit: bool = True) -> TaskJob:
        task = self.get(task_id)
        if task.status not in {"queued", "running"}:
            raise AppError("INVALID_TASK_STATE", "只有 queued/running 任务可以成功结束", status.HTTP_409_CONFLICT)
        if task.started_at is None:
            task.started_at = utcnow()
        task.status = "succeeded"
        task.result_summary = result_summary
        task.error_message = None
        task.finished_at = utcnow()
        self._finish_write(task, commit)
        return task

    def mark_failed(self, task_id: str, error_message: str, *, commit: bool = True) -> TaskJob:
        task = self.get(task_id)
        if task.status not in {"queued", "running"}:
            raise AppError("INVALID_TASK_STATE", "只有 queued/running 任务可以失败结束", status.HTTP_409_CONFLICT)
        if task.started_at is None:
            task.started_at = utcnow()
        task.status = "failed"
        task.error_message = error_message
        task.finished_at = utcnow()
        self._finish_write(task, commit)
        return task

    def _finish_write(self, task: TaskJob, commit: bool) -> None:
        if commit:
            self.db.commit()
            self.db.refresh(task)
        else:
            self.db.flush()
