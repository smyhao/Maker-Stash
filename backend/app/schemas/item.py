from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AttributeInput(BaseModel):
    name: str
    key: str
    value: str | None = None
    value_type: str | None = "text"
    unit: str | None = None


class ItemCreate(BaseModel):
    name: str
    category: str | int | None = None
    location_code: str | None = None
    location_text: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    status: str = "normal"
    description: str | None = None
    attributes: list[AttributeInput] = []
    tags: list[str] = []
    note: str | None = None


class ItemUpdate(BaseModel):
    name: str | None = None
    category_id: int | None = None
    location_id: int | None = None
    location_text: str | None = None
    quantity: Decimal | None = None
    unit: str | None = None
    status: str | None = None
    description: str | None = None
    need_restock: bool | None = None
    is_favorite: bool | None = None


class ItemMove(BaseModel):
    location_code: str | None = None
    location_text: str | None = None
    note: str | None = None
    source: str = "api"


class QuantityAdd(BaseModel):
    amount: Decimal
    unit: str | None = None
    note: str | None = None
    source: str = "api"


class QuantityAdjust(BaseModel):
    quantity: Decimal
    unit: str | None = None
    note: str | None = None
    source: str = "api"


class NoteCreate(BaseModel):
    note_type: str = "note"
    content: str
    source: str = "api"
    operator: str | None = None
    metadata_json: str | None = None


class ItemRead(BaseModel):
    id: int
    code: str
    name: str
    category_id: int | None
    location_id: int | None
    location_text: str | None
    quantity: Decimal | None
    unit: str | None
    status: str
    description: str | None
    need_restock: bool
    is_favorite: bool
    cover_attachment_id: int | None
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
