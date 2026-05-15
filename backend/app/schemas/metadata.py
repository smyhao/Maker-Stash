from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagCreate(BaseModel):
    name: str
    slug: str | None = None


class TagRead(BaseModel):
    id: int
    name: str
    slug: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemTagsUpdate(BaseModel):
    tags: list[str]


class AliasCreate(BaseModel):
    alias: str


class AliasRead(BaseModel):
    id: int
    item_id: int
    alias: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IdentifierCreate(BaseModel):
    type: str
    value: str
    description: str | None = None


class IdentifierRead(BaseModel):
    id: int
    item_id: int
    type: str
    value: str
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
