from typing import TypeVar

from pydantic import BaseModel

from app.core.errors import AppError


T = TypeVar("T", bound=BaseModel)


def apply_idempotency_key(payload: T, idempotency_key: str | None) -> T:
    if not idempotency_key:
        return payload
    request_id = getattr(payload, "request_id", None)
    if request_id and request_id != idempotency_key:
        raise AppError("IDEMPOTENCY_KEY_MISMATCH", "request_id 与 Idempotency-Key 不一致")
    return payload.model_copy(update={"request_id": idempotency_key})
