import hashlib
import hmac
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.errors import AppError
from app.models.api_token import ApiToken


bearer = HTTPBearer(auto_error=False)
TOKEN_HASH_PREFIX = "sha256$"
WEB_UI_CLIENT_HEADER = "x-maker-stash-client"
WEB_UI_CLIENT_VALUE = "web"


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return f"{TOKEN_HASH_PREFIX}{digest}"


def verify_token(token: str, token_hash: str) -> bool:
    if not token_hash.startswith(TOKEN_HASH_PREFIX):
        return False
    expected = hash_token(token)
    return hmac.compare_digest(expected, token_hash)


def require_api_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> None:
    settings = get_settings()
    if not settings.api_token_enabled:
        return
    if not settings.web_ui_token_required and request.headers.get(WEB_UI_CLIENT_HEADER) == WEB_UI_CLIENT_VALUE:
        return
    if not settings.api_token_require_all and request.url.path in {
        "/api/health",
        "/api/system/info",
    }:
        return
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("INVALID_TOKEN", "缺少 API Token", status.HTTP_401_UNAUTHORIZED)

    tokens = db.scalars(select(ApiToken).where(ApiToken.enabled.is_(True))).all()
    for api_token in tokens:
        if verify_token(credentials.credentials, api_token.token_hash):
            api_token.last_used_at = datetime.now(timezone.utc)
            db.commit()
            return
    raise AppError("INVALID_TOKEN", "API Token 无效", status.HTTP_401_UNAUTHORIZED)
