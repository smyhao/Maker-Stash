from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.request_context import apply_idempotency_key
from app.core.response import ok
from app.schemas.workflow import WorkflowConfirm, WorkflowPlanCreate
from app.services.task_service import TaskService
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/plans")
def create_plan(
    payload: WorkflowPlanCreate,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> dict:
    payload = apply_idempotency_key(payload, idempotency_key)
    service = WorkflowService(db)
    plan = service.plan(payload)
    return ok({"plan": service.read(plan)})


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> dict:
    service = WorkflowService(db)
    plan = service.get(plan_id)
    return ok({"plan": service.read(plan), "result": service.confirm_result(plan)})


@router.post("/plans/{plan_id}/confirm")
def confirm_plan(
    plan_id: str,
    payload: WorkflowConfirm,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> dict:
    payload = apply_idempotency_key(payload, idempotency_key)
    service = WorkflowService(db)
    plan = service.confirm(plan_id, payload)
    task = TaskService(db).get(plan.task_id) if plan.task_id else None
    task_data = {
        "task_id": task.task_id,
        "status": task.status,
        "job_type": task.job_type,
        "error_message": task.error_message,
    } if task else None
    return ok({"plan": service.read(plan), "task": task_data, "result": service.confirm_result(plan)})
