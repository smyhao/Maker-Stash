from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str
    slug: str
    code_prefix: str
    parent_id: int | None = None
    sort_order: int = 0
    description: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    sort_order: int | None = None
    description: str | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    slug: str
    code_prefix: str
    parent_id: int | None
    sort_order: int
    description: str | None
    is_system: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryTreeNode(CategoryRead):
    children: list["CategoryTreeNode"] = Field(default_factory=list)
