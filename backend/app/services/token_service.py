from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.core.security import generate_token, hash_token
from app.models.api_token import ApiToken
from app.schemas.token import TokenCreate, TokenUpdate


class TokenService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[ApiToken]:
        return list(
            self.db.scalars(select(ApiToken).order_by(ApiToken.created_at.desc()))
        )

    def get(self, token_id: int) -> ApiToken:
        token = self.db.get(ApiToken, token_id)
        if token is None:
            raise NotFoundError("TOKEN_NOT_FOUND", "Token 不存在")
        return token

    def create(self, payload: TokenCreate) -> tuple[ApiToken, str]:
        exists = self.db.scalar(select(ApiToken).where(ApiToken.name == payload.name))
        if exists:
            raise AppError("DUPLICATE_NAME", "Token 名称已存在")
        plaintext = generate_token()
        token_hash = hash_token(plaintext)
        api_token = ApiToken(
            name=payload.name,
            token_hash=token_hash,
            description=payload.description,
        )
        self.db.add(api_token)
        self.db.commit()
        self.db.refresh(api_token)
        return api_token, plaintext

    def update(self, token_id: int, payload: TokenUpdate) -> ApiToken:
        api_token = self.get(token_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(api_token, key, value)
        self.db.commit()
        self.db.refresh(api_token)
        return api_token

    def delete(self, token_id: int) -> None:
        api_token = self.get(token_id)
        self.db.delete(api_token)
        self.db.commit()
