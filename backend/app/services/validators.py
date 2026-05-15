import re

from app.core.errors import AppError


CODE_RE = re.compile(r"^[A-Z0-9._-]+$")


def validate_code(value: str, field: str = "code") -> None:
    if not CODE_RE.fullmatch(value):
        raise AppError(
            "VALIDATION_ERROR",
            f"{field} 只能包含 A-Z、0-9、点、横线和下划线",
        )
