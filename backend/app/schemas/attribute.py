from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttributeDefinitionCreate(BaseModel):
    category_id: int
    name: str
    key: str
    field_type: str = "text"
    unit: str | None = None
    options_json: str | None = None
    required: bool = False
    sort_order: int = 0


class AttributeDefinitionUpdate(BaseModel):
    name: str | None = None
    field_type: str | None = None
    unit: str | None = None
    options_json: str | None = None
    required: bool | None = None
    sort_order: int | None = None
    is_enabled: bool | None = None


class AttributeDefinitionRead(BaseModel):
    id: int
    category_id: int
    name: str
    key: str
    field_type: str
    unit: str | None
    options_json: str | None
    required: bool
    sort_order: int
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemAttributeValueCreate(BaseModel):
    name: str
    key: str
    value: str | None = None
    value_type: str | None = "text"
    unit: str | None = None
    attribute_definition_id: int | None = None
    sort_order: int = 0


class ItemAttributeValueUpdate(BaseModel):
    name: str | None = None
    value: str | None = None
    value_type: str | None = None
    unit: str | None = None
    sort_order: int | None = None


class ItemAttributeValueRead(BaseModel):
    id: int
    item_id: int
    attribute_definition_id: int | None
    name: str
    key: str
    value: str | None
    value_type: str | None
    unit: str | None
    sort_order: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
