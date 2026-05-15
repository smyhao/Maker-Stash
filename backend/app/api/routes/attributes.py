from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.attribute import (
    AttributeDefinitionCreate,
    AttributeDefinitionRead,
    AttributeDefinitionUpdate,
    ItemAttributeValueCreate,
    ItemAttributeValueRead,
    ItemAttributeValueUpdate,
)
from app.services.attribute_service import AttributeDefinitionService, ItemAttributeService

router = APIRouter(tags=["attributes"])


@router.get("/attribute-definitions")
def list_attribute_definitions(
    category_id: int | None = None,
    db: Session = Depends(get_db),
) -> dict:
    definitions = [
        AttributeDefinitionRead.model_validate(item).model_dump()
        for item in AttributeDefinitionService(db).list(category_id)
    ]
    return ok({"attribute_definitions": definitions})


@router.get("/categories/{category_id}/attribute-definitions")
def list_category_attribute_definitions(
    category_id: int,
    db: Session = Depends(get_db),
) -> dict:
    definitions = [
        AttributeDefinitionRead.model_validate(item).model_dump()
        for item in AttributeDefinitionService(db).list(category_id)
    ]
    return ok({"attribute_definitions": definitions})


@router.post("/attribute-definitions")
def create_attribute_definition(
    payload: AttributeDefinitionCreate,
    db: Session = Depends(get_db),
) -> dict:
    definition = AttributeDefinitionService(db).create(payload)
    return ok(AttributeDefinitionRead.model_validate(definition).model_dump())


@router.patch("/attribute-definitions/{definition_id}")
def update_attribute_definition(
    definition_id: int,
    payload: AttributeDefinitionUpdate,
    db: Session = Depends(get_db),
) -> dict:
    definition = AttributeDefinitionService(db).update(definition_id, payload)
    return ok(AttributeDefinitionRead.model_validate(definition).model_dump())


@router.delete("/attribute-definitions/{definition_id}")
def delete_attribute_definition(definition_id: int, db: Session = Depends(get_db)) -> dict:
    AttributeDefinitionService(db).delete(definition_id)
    return ok({"deleted": True})


@router.get("/items/{id_or_code}/attributes")
def list_item_attributes(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    values = [
        ItemAttributeValueRead.model_validate(item).model_dump()
        for item in ItemAttributeService(db).list(id_or_code)
    ]
    return ok({"attributes": values})


@router.post("/items/{id_or_code}/attributes")
def create_item_attribute(
    id_or_code: str,
    payload: ItemAttributeValueCreate,
    db: Session = Depends(get_db),
) -> dict:
    value = ItemAttributeService(db).create(id_or_code, payload)
    return ok(ItemAttributeValueRead.model_validate(value).model_dump())


@router.patch("/item-attributes/{attribute_id}")
def update_item_attribute(
    attribute_id: int,
    payload: ItemAttributeValueUpdate,
    db: Session = Depends(get_db),
) -> dict:
    value = ItemAttributeService(db).update(attribute_id, payload)
    return ok(ItemAttributeValueRead.model_validate(value).model_dump())


@router.delete("/item-attributes/{attribute_id}")
def delete_item_attribute(attribute_id: int, db: Session = Depends(get_db)) -> dict:
    ItemAttributeService(db).delete(attribute_id)
    return ok({"deleted": True})
