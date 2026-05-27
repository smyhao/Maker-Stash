from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

from app.schemas.common import WriteMetadata


class AttributeInput(BaseModel):
    name: str
    key: str
    value: str | None = None
    value_type: str | None = "text"
    unit: str | None = None


class ItemCreate(WriteMetadata):
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

    @field_validator("quantity")
    @classmethod
    def quantity_must_not_be_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("数量不能为负")
        return value


class ItemUpdate(WriteMetadata):
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

    @field_validator("quantity")
    @classmethod
    def quantity_must_not_be_negative(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value < 0:
            raise ValueError("数量不能为负")
        return value


class ItemMove(WriteMetadata):
    location_code: str | None = None
    location_text: str | None = None
    note: str | None = None


class QuantityAdd(WriteMetadata):
    amount: Decimal
    unit: str | None = None
    note: str | None = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("数量变更必须大于 0")
        return value


class QuantityAdjust(WriteMetadata):
    quantity: Decimal
    unit: str | None = None
    note: str | None = None

    @field_validator("quantity")
    @classmethod
    def quantity_must_not_be_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("数量不能为负")
        return value


class NoteCreate(WriteMetadata):
    note_type: str = "note"
    content: str
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

    @field_serializer("quantity")
    @classmethod
    def serialize_quantity(cls, v: Decimal | None) -> str | None:
        if v is None:
            return None
        s = format(v, "f")
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
