from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import WriteMetadata


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
    layout_type: str | None
    layout_rows: int | None
    layout_columns: int | None
    appearance_color: str | None
    appearance_icon: str | None
    is_slot: bool
    slot_key: str | None
    slot_order: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LocationTreeNode(LocationRead):
    children: list["LocationTreeNode"] = Field(default_factory=list)


class ContainerLayout(BaseModel):
    layout_type: Literal["grid", "row"] = "grid"
    layout_rows: int = Field(default=3, ge=1, le=26)
    layout_columns: int = Field(default=5, ge=1, le=30)
    appearance_color: str = "sage"
    appearance_icon: Literal["box", "drawer", "shelf"] = "box"

    @field_validator("appearance_color")
    @classmethod
    def validate_appearance_color(cls, value: str) -> str:
        if value in {"sage", "clay", "sand", "ink"}:
            return value
        if re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            return value.upper()
        raise ValueError("appearance_color 必须是预设色或 #RRGGBB 格式")

    @model_validator(mode="after")
    def validate_row_layout(self) -> "ContainerLayout":
        if self.layout_type == "row":
            self.layout_rows = 1
        return self


class ContainerCreate(ContainerLayout):
    name: str
    code: str
    parent_code: str | None = None
    type: str | None = "box"
    description: str | None = None
    sort_order: int = 0


class SlotAssignment(BaseModel):
    item_code: str
    slot_key: str


class ContainerConvert(ContainerLayout):
    assignments: list[SlotAssignment] = Field(default_factory=list)


class ContainerUpdate(ContainerLayout):
    pass


class SlotSwap(WriteMetadata):
    source_item_code: str
    target_slot_key: str
