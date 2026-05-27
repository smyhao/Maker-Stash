from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.audit import AuditLog, IdempotencyRecord


@dataclass(frozen=True)
class WriteContext:
    source: str = "api"
    module: str | None = None
    operator: str | None = None
    request_id: str | None = None

    @classmethod
    def from_payload(cls, payload: Any, default_source: str = "api") -> "WriteContext":
        return cls(
            source=getattr(payload, "source", None) or default_source,
            module=getattr(payload, "module", None),
            operator=getattr(payload, "operator", None),
            request_id=getattr(payload, "request_id", None),
        )


class IdempotencyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_existing(self, ctx: WriteContext, action: str) -> IdempotencyRecord | None:
        if not ctx.request_id:
            return None
        record = self.db.scalar(
            select(IdempotencyRecord).where(IdempotencyRecord.request_id == ctx.request_id)
        )
        if record is None:
            return None
        if record.action != action:
            raise AppError(
                "IDEMPOTENCY_KEY_CONFLICT",
                "幂等键已被其他写操作使用",
                status.HTTP_409_CONFLICT,
            )
        return record

    def remember(
        self,
        ctx: WriteContext,
        action: str,
        target_type: str,
        target_id: int | str,
    ) -> None:
        if not ctx.request_id:
            return
        self.db.add(
            IdempotencyRecord(
                request_id=ctx.request_id,
                action=action,
                target_type=target_type,
                target_id=str(target_id),
                source=ctx.source,
                module=ctx.module,
                operator=ctx.operator,
            )
        )


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def record(
        self,
        ctx: WriteContext,
        *,
        action: str,
        target_type: str,
        target_id: int | str,
        before: dict[str, Any] | None,
        after: dict[str, Any] | None,
    ) -> None:
        self.db.add(
            AuditLog(
                who=ctx.operator,
                source=ctx.source,
                module=ctx.module,
                action=action,
                target_type=target_type,
                target_id=str(target_id),
                before_json=_dump_json(before),
                after_json=_dump_json(after),
                request_id=ctx.request_id,
            )
        )


def _dump_json(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=_json_default)


def _json_default(value: Any) -> str:
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)
