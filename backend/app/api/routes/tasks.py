from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.request_context import apply_idempotency_key
from app.core.response import ok
from app.schemas.task import TaskCreate, TaskRead, TaskStatusRead
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("")
def submit_task(
    payload: TaskCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> dict:
    payload = apply_idempotency_key(payload, idempotency_key)
    task = TaskService(db).submit(payload)
    data = TaskRead.model_validate(task).model_dump()
    return ok({"task": data, "task_id": task.task_id, "status": task.status})


@router.get("/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)) -> dict:
    task = TaskService(db).get(task_id)
    return ok({"task": TaskRead.model_validate(task).model_dump()})


@router.get("/{task_id}/status")
def get_task_status(task_id: str, db: Session = Depends(get_db)) -> dict:
    task = TaskService(db).get(task_id)
    status_data = TaskStatusRead.model_validate(task).model_dump()
    if task.status == "failed":
        status_data["error"] = {
            "code": "TASK_FAILED",
            "message": task.error_message or "任务执行失败",
        }
    return ok({"task": status_data})
