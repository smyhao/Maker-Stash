from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.attribute import AttributeDefinition, ItemAttributeValue
from app.schemas.attribute import (
    AttributeDefinitionCreate,
    AttributeDefinitionUpdate,
    ItemAttributeValueCreate,
    ItemAttributeValueUpdate,
)
from app.services.category_service import CategoryService
from app.services.item_service import ItemService


ALLOWED_FIELD_TYPES = {"text", "number", "select", "multi", "date", "url", "boolean", "textarea"}


class AttributeDefinitionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, category_id: int | None = None) -> list[AttributeDefinition]:
        stmt = select(AttributeDefinition)
        if category_id is not None:
            stmt = stmt.where(AttributeDefinition.category_id == category_id)
        return list(self.db.scalars(stmt.order_by(AttributeDefinition.sort_order, AttributeDefinition.id)))

    def get(self, definition_id: int) -> AttributeDefinition:
        definition = self.db.get(AttributeDefinition, definition_id)
        if definition is None:
            raise NotFoundError("ATTRIBUTE_DEFINITION_NOT_FOUND", "属性模板不存在")
        return definition

    def create(self, payload: AttributeDefinitionCreate) -> AttributeDefinition:
        CategoryService(self.db).get(payload.category_id)
        self._validate_field_type(payload.field_type)
        exists = self.db.scalar(
            select(AttributeDefinition).where(
                AttributeDefinition.category_id == payload.category_id,
                AttributeDefinition.key == payload.key,
            )
        )
        if exists:
            raise AppError("DUPLICATE_CODE", "属性 key 已存在")
        definition = AttributeDefinition(**payload.model_dump(), is_enabled=True)
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)
        return definition

    def update(self, definition_id: int, payload: AttributeDefinitionUpdate) -> AttributeDefinition:
        definition = self.get(definition_id)
        data = payload.model_dump(exclude_unset=True)
        if "field_type" in data and data["field_type"]:
            self._validate_field_type(data["field_type"])
        for key, value in data.items():
            setattr(definition, key, value)
        self.db.commit()
        self.db.refresh(definition)
        return definition

    def delete(self, definition_id: int) -> None:
        definition = self.get(definition_id)
        used = self.db.scalar(
            select(ItemAttributeValue.id).where(
                ItemAttributeValue.attribute_definition_id == definition.id
            )
        )
        if used:
            definition.is_enabled = False
        else:
            self.db.delete(definition)
        self.db.commit()

    def _validate_field_type(self, field_type: str) -> None:
        if field_type not in ALLOWED_FIELD_TYPES:
            raise AppError("VALIDATION_ERROR", f"不支持的字段类型：{field_type}")


class ItemAttributeService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, id_or_code: str) -> list[ItemAttributeValue]:
        item = ItemService(self.db).get(id_or_code)
        return list(
            self.db.scalars(
                select(ItemAttributeValue)
                .where(ItemAttributeValue.item_id == item.id)
                .order_by(ItemAttributeValue.sort_order, ItemAttributeValue.id)
            )
        )

    def create(self, id_or_code: str, payload: ItemAttributeValueCreate) -> ItemAttributeValue:
        item = ItemService(self.db).get(id_or_code)
        exists = self.db.scalar(
            select(ItemAttributeValue).where(
                ItemAttributeValue.item_id == item.id,
                ItemAttributeValue.key == payload.key,
            )
        )
        if exists:
            raise AppError("DUPLICATE_CODE", "物品属性 key 已存在")
        value = ItemAttributeValue(item_id=item.id, **payload.model_dump())
        self.db.add(value)
        self.db.commit()
        self.db.refresh(value)
        return value

    def update(self, attribute_id: int, payload: ItemAttributeValueUpdate) -> ItemAttributeValue:
        value = self.db.get(ItemAttributeValue, attribute_id)
        if value is None:
            raise NotFoundError("ATTRIBUTE_VALUE_NOT_FOUND", "物品属性不存在")
        for key, new_value in payload.model_dump(exclude_unset=True).items():
            setattr(value, key, new_value)
        self.db.commit()
        self.db.refresh(value)
        return value

    def delete(self, attribute_id: int) -> None:
        value = self.db.get(ItemAttributeValue, attribute_id)
        if value:
            self.db.delete(value)
            self.db.commit()
