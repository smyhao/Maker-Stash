from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TokenCreate(BaseModel):
    name: str
    description: str | None = None


class TokenUpdate(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    description: str | None = None


class TokenRead(BaseModel):
    id: int
    name: str
    enabled: bool
    description: str | None
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime
    is_current: bool = False

    model_config = ConfigDict(from_attributes=True)


class TokenCreated(TokenRead):
    token: str
