from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.common import WriteMetadata


class BatchImportRow(BaseModel):
    code: str | None = None
    name: str | None = None
    category: str | int | None = None
    location_code: str | None = None
    location_text: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    description: str | None = None
    tags: list[str] = []
    note: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_not_be_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("数量不能为负")
        return value


class BatchOutboundRow(BaseModel):
    id_or_code: str
    amount: Decimal
    unit: str | None = None
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("出库数量必须大于 0")
        return value


class AgentAction(BaseModel):
    action: str
    target_type: str | None = None
    target_ref: str | None = None
    summary: str
    risk: str | None = None


class WorkflowPlanCreate(WriteMetadata):
    workflow_type: Literal["batch_import", "batch_outbound", "agent_operation"]
    import_rows: list[BatchImportRow] = []
    outbound_rows: list[BatchOutboundRow] = []
    agent_actions: list[AgentAction] = []


class WorkflowConfirm(WriteMetadata):
    confirm_token: str


class WorkflowPlanRead(BaseModel):
    plan_id: str
    workflow_type: str
    status: str
    summary: dict[str, int]
    creates: list[dict[str, Any]]
    updates: list[dict[str, Any]]
    skips: list[dict[str, Any]]
    failures: list[dict[str, Any]]
    risks: list[str]
    confirm_token: str
    task_id: str | None
    source: str
    module: str | None
    operator: str | None
    request_id: str | None
    created_at: datetime
    confirmed_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
