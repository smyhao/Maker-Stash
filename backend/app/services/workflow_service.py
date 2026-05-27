from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.item import Item
from app.models.mixins import utcnow
from app.models.workflow import WorkflowPlan
from app.schemas.item import ItemCreate, ItemUpdate, QuantityAdd
from app.schemas.task import TaskCreate
from app.schemas.workflow import BatchImportRow, BatchOutboundRow, WorkflowConfirm, WorkflowPlanCreate
from app.services.audit_service import WriteContext
from app.services.category_service import CategoryService
from app.services.item_service import ItemService
from app.services.location_service import LocationService
from app.services.task_service import TaskService


WORKFLOW_TYPES = {"batch_import", "batch_outbound", "agent_operation"}


class WorkflowService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def plan(self, payload: WorkflowPlanCreate) -> WorkflowPlan:
        ctx = WriteContext.from_payload(payload)
        if ctx.request_id:
            existing = self.db.scalar(select(WorkflowPlan).where(WorkflowPlan.request_id == ctx.request_id))
            if existing:
                return existing
        if payload.workflow_type not in WORKFLOW_TYPES:
            raise AppError("UNSUPPORTED_WORKFLOW_TYPE", f"不支持的工作流类型：{payload.workflow_type}")

        plan_data = self._build_plan(payload)
        plan = WorkflowPlan(
            plan_id=f"plan-{uuid4().hex}",
            workflow_type=payload.workflow_type,
            status="planned",
            plan_json=_dump_json(plan_data),
            confirm_token=f"confirm-{uuid4().hex}",
            source=ctx.source,
            module=ctx.module,
            operator=ctx.operator,
            request_id=ctx.request_id,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def get(self, plan_id: str) -> WorkflowPlan:
        plan = self.db.scalar(select(WorkflowPlan).where(WorkflowPlan.plan_id == plan_id))
        if plan is None:
            raise NotFoundError("PLAN_NOT_FOUND", f"计划不存在：{plan_id}")
        return plan

    def confirm(self, plan_id: str, payload: WorkflowConfirm) -> WorkflowPlan:
        plan = self.get(plan_id)
        if payload.confirm_token != plan.confirm_token:
            raise AppError("PLAN_CONFIRM_TOKEN_INVALID", "确认标识不匹配", status.HTTP_409_CONFLICT)
        if plan.status == "confirmed":
            return plan
        plan_data = self._plan_data(plan)
        if plan_data["failures"]:
            raise AppError("PLAN_HAS_FAILURES", "计划包含失败项，不能确认执行", status.HTTP_409_CONFLICT)

        ctx = WriteContext(
            source=payload.source or plan.source,
            module=payload.module or plan.module,
            operator=payload.operator or plan.operator,
            request_id=payload.request_id or f"{plan.plan_id}:confirm",
        )
        task_service = TaskService(self.db)
        task = task_service.submit(
            TaskCreate(
                job_type=plan.workflow_type,
                input_summary=f"confirm {plan.plan_id}",
                source=ctx.source,
                module=ctx.module,
                operator=ctx.operator,
                request_id=f"{ctx.request_id}:task",
            )
        )
        task_service.mark_running(task.task_id)
        try:
            result = self._execute_plan(plan, plan_data, ctx)
            task_service.mark_succeeded(task.task_id, _dump_json(result["summary"]), commit=False)
        except Exception as exc:
            self.db.rollback()
            task_service.mark_failed(task.task_id, _workflow_error_message(exc))
            raise

        plan.status = "confirmed"
        plan.task_id = task.task_id
        plan.result_json = _dump_json(result)
        plan.confirmed_at = utcnow()
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def read(self, plan: WorkflowPlan) -> dict[str, Any]:
        data = self._plan_data(plan)
        return {
            "plan_id": plan.plan_id,
            "workflow_type": plan.workflow_type,
            "status": plan.status,
            "summary": data["summary"],
            "creates": data["creates"],
            "updates": data["updates"],
            "skips": data["skips"],
            "failures": data["failures"],
            "risks": data["risks"],
            "confirm_token": plan.confirm_token,
            "task_id": plan.task_id,
            "source": plan.source,
            "module": plan.module,
            "operator": plan.operator,
            "request_id": plan.request_id,
            "created_at": plan.created_at,
            "confirmed_at": plan.confirmed_at,
        }

    def confirm_result(self, plan: WorkflowPlan) -> dict[str, Any] | None:
        if not plan.result_json:
            return None
        return json.loads(plan.result_json)

    def _build_plan(self, payload: WorkflowPlanCreate) -> dict[str, Any]:
        if payload.workflow_type == "batch_import":
            return self._plan_batch_import(payload.import_rows)
        if payload.workflow_type == "batch_outbound":
            return self._plan_batch_outbound(payload.outbound_rows)
        return self._plan_agent_operation(payload.agent_actions)

    def _plan_batch_import(self, rows: list[BatchImportRow]) -> dict[str, Any]:
        plan = _empty_plan()
        if not rows:
            plan["failures"].append({"row": None, "code": "EMPTY_INPUT", "message": "import_rows 不能为空"})
        for index, row in enumerate(rows):
            if not row.name:
                plan["failures"].append({"row": index, "code": "NAME_REQUIRED", "message": "名称不能为空"})
                continue
            category = CategoryService(self.db).find_by_any(row.category)
            if row.category is not None and category is None:
                plan["failures"].append({"row": index, "code": "CATEGORY_NOT_FOUND", "message": f"分类不存在：{row.category}"})
                continue
            location = None
            if row.location_code:
                try:
                    location = LocationService(self.db).get_by_code(row.location_code)
                except NotFoundError:
                    plan["failures"].append({"row": index, "code": "LOCATION_NOT_FOUND", "message": f"位置不存在：{row.location_code}"})
                    continue
            existing = self.db.scalar(select(Item).where(Item.code == row.code)) if row.code else None
            if existing:
                update_payload = {
                    "name": row.name,
                    "category_id": category.id if category else None,
                    "location_id": location.id if location else None,
                    "location_text": row.location_text,
                    "quantity": _decimal_to_str(row.quantity),
                    "unit": row.unit,
                    "description": row.description,
                }
                before = ItemService(self.db)._item_snapshot(existing)
                after = {**before, **{k: v for k, v in update_payload.items() if v is not None}}
                if before == after:
                    plan["skips"].append({"row": index, "reason": "unchanged", "target": row.code})
                else:
                    plan["updates"].append({"row": index, "target": row.code, "before": before, "after": after, "payload": update_payload})
            else:
                create_payload = {
                    "name": row.name,
                    "category": row.category,
                    "location_code": row.location_code,
                    "location_text": row.location_text,
                    "quantity": _decimal_to_str(row.quantity),
                    "unit": row.unit,
                    "description": row.description,
                    "tags": row.tags,
                    "note": row.note,
                }
                plan["creates"].append({"row": index, "target": None, "after": create_payload, "payload": create_payload})
        _finish_plan(plan)
        return plan

    def _plan_batch_outbound(self, rows: list[BatchOutboundRow]) -> dict[str, Any]:
        plan = _empty_plan()
        if not rows:
            plan["failures"].append({"row": None, "code": "EMPTY_INPUT", "message": "outbound_rows 不能为空"})
        for index, row in enumerate(rows):
            try:
                item = ItemService(self.db).get(row.id_or_code)
            except NotFoundError:
                plan["failures"].append({"row": index, "code": "ITEM_NOT_FOUND", "message": f"物品不存在：{row.id_or_code}"})
                continue
            if item.is_archived:
                plan["failures"].append({"row": index, "code": "ARCHIVED_ITEM_QUANTITY_FORBIDDEN", "message": "物品已归档，不能出库"})
                continue
            current = item.quantity or Decimal("0")
            after_quantity = current - row.amount
            if after_quantity < 0:
                plan["failures"].append({"row": index, "code": "NEGATIVE_QUANTITY_NOT_ALLOWED", "message": "出库后库存不能为负数"})
                continue
            before = ItemService(self.db)._item_snapshot(item)
            after = {**before, "quantity": _decimal_to_str(after_quantity), "unit": row.unit or item.unit}
            if after_quantity == 0:
                plan["risks"].append(f"{item.code} 本次出库后库存为 0")
            plan["updates"].append(
                {
                    "row": index,
                    "target": item.code,
                    "before": before,
                    "after": after,
                    "payload": {
                        "id_or_code": item.code,
                        "amount": _decimal_to_str(row.amount),
                        "unit": row.unit,
                        "note": row.note,
                    },
                }
            )
        _finish_plan(plan)
        return plan

    def _plan_agent_operation(self, actions) -> dict[str, Any]:
        plan = _empty_plan()
        if not actions:
            plan["failures"].append({"row": None, "code": "EMPTY_INPUT", "message": "agent_actions 不能为空"})
        for index, action in enumerate(actions):
            entry = action.model_dump()
            plan["updates"].append({"row": index, "target": action.target_ref, "after": entry, "payload": entry})
            if action.risk:
                plan["risks"].append(action.risk)
        _finish_plan(plan)
        return plan

    def _execute_plan(self, plan: WorkflowPlan, plan_data: dict[str, Any], ctx: WriteContext) -> dict[str, Any]:
        result = {"created_items": [], "updated_items": [], "skipped": plan_data["skips"], "summary": {}}
        if plan.workflow_type == "batch_import":
            for index, entry in enumerate(plan_data["creates"]):
                payload = entry["payload"]
                item = ItemService(self.db).create(
                    ItemCreate(**payload, source=ctx.source, module=ctx.module, operator=ctx.operator, request_id=f"{ctx.request_id}:create:{index}"),
                    commit=False,
                )
                result["created_items"].append({"code": item.code, "name": item.name})
            for index, entry in enumerate(plan_data["updates"]):
                payload = {k: v for k, v in entry["payload"].items() if v is not None}
                item = ItemService(self.db).update(
                    entry["target"],
                    ItemUpdate(**payload, source=ctx.source, module=ctx.module, operator=ctx.operator, request_id=f"{ctx.request_id}:update:{index}"),
                    commit=False,
                )
                result["updated_items"].append({"code": item.code, "name": item.name})
        elif plan.workflow_type == "batch_outbound":
            for index, entry in enumerate(plan_data["updates"]):
                payload = entry["payload"]
                item = ItemService(self.db).use_quantity(
                    payload["id_or_code"],
                    QuantityAdd(
                        amount=Decimal(payload["amount"]),
                        unit=payload.get("unit"),
                        note=payload.get("note"),
                        source=ctx.source,
                        module=ctx.module,
                        operator=ctx.operator,
                        request_id=f"{ctx.request_id}:use:{index}",
                    ),
                    commit=False,
                )
                result["updated_items"].append({"code": item.code, "quantity": _decimal_to_str(item.quantity)})
        else:
            result["updated_items"] = plan_data["updates"]
        result["summary"] = {
            "created": len(result["created_items"]),
            "updated": len(result["updated_items"]),
            "skipped": len(result["skipped"]),
            "failed": 0,
        }
        return result

    def _plan_data(self, plan: WorkflowPlan) -> dict[str, Any]:
        return json.loads(plan.plan_json)


def _empty_plan() -> dict[str, Any]:
    return {"summary": {}, "creates": [], "updates": [], "skips": [], "failures": [], "risks": []}


def _finish_plan(plan: dict[str, Any]) -> None:
    plan["summary"] = {
        "creates": len(plan["creates"]),
        "updates": len(plan["updates"]),
        "skips": len(plan["skips"]),
        "failures": len(plan["failures"]),
        "risks": len(plan["risks"]),
    }
    if plan["failures"]:
        plan["risks"].append("计划包含失败项，确认执行前需要修正输入")


def _decimal_to_str(value: Decimal | None) -> str | None:
    if value is None:
        return None
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _dump_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _workflow_error_message(exc: Exception) -> str:
    if isinstance(exc, AppError):
        return exc.message
    return str(exc) or exc.__class__.__name__
