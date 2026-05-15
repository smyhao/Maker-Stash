from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel

from app.core.errors import AppError


class ErrorBody(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    success: bool
    data: Any | None = None
    message: str | None = "ok"
    error: ErrorBody | None = None


def ok(data: Any = None, message: str = "ok") -> dict[str, Any]:
    return {"success": True, "data": data, "message": message}


def fail(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message}}


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=fail(exc.code, exc.message),
    )


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    location = ".".join(str(part) for part in first_error.get("loc", []))
    message = first_error.get("msg", "请求参数无效")
    if location:
        message = f"{location}: {message}"
    return JSONResponse(
        status_code=422,
        content=fail("VALIDATION_ERROR", message),
    )
