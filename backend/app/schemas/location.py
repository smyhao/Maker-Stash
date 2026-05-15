from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LocationCreate(BaseModel):
    name: str
    code: str
    parent_code: str | None = None
    type: str | None = None
    description: str | None = None
    sort_order: int = 0


class LocationUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    description: str | None = None
    sort_order: int | None = None


class LocationRead(BaseModel):
    id: int
    name: str
    code: str
    full_code: str
    parent_id: int | None
    type: str | None
    description: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocationTreeNode(LocationRead):
    children: list["LocationTreeNode"] = Field(default_factory=list)
