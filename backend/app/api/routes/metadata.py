from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.item import ItemRead
from app.schemas.metadata import (
    AliasCreate,
    AliasRead,
    IdentifierCreate,
    IdentifierRead,
    ItemTagsUpdate,
    TagCreate,
    TagRead,
)
from app.services.metadata_service import AliasService, IdentifierService, TagService

router = APIRouter(tags=["metadata"])


@router.get("/tags")
def list_tags(db: Session = Depends(get_db)) -> dict:
    tags = [TagRead.model_validate(tag).model_dump() for tag in TagService(db).list()]
    return ok({"tags": tags})


@router.post("/tags")
def create_tag(payload: TagCreate, db: Session = Depends(get_db)) -> dict:
    tag = TagService(db).create(payload)
    return ok(TagRead.model_validate(tag).model_dump())


@router.delete("/tags/{tag_id}")
def delete_tag(tag_id: int, db: Session = Depends(get_db)) -> dict:
    TagService(db).delete(tag_id)
    return ok({"deleted": True})


@router.get("/items/by-identifier/{identifier}")
def find_item_by_identifier(identifier: str, db: Session = Depends(get_db)) -> dict:
    item = IdentifierService(db).find_item(identifier)
    return ok(ItemRead.model_validate(item).model_dump())


@router.get("/items/{id_or_code}/tags")
def list_item_tags(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    tags = [
        TagRead.model_validate(tag).model_dump()
        for tag in TagService(db).item_tags(id_or_code)
    ]
    return ok({"tags": tags})


@router.post("/items/{id_or_code}/tags")
def add_item_tags(
    id_or_code: str,
    payload: ItemTagsUpdate,
    db: Session = Depends(get_db),
) -> dict:
    tags = [
        TagRead.model_validate(tag).model_dump()
        for tag in TagService(db).add_item_tags(id_or_code, payload.tags)
    ]
    return ok({"tags": tags})


@router.delete("/items/{id_or_code}/tags/{tag}")
def remove_item_tag(id_or_code: str, tag: str, db: Session = Depends(get_db)) -> dict:
    TagService(db).remove_item_tag(id_or_code, tag)
    return ok({"deleted": True})


@router.get("/items/{id_or_code}/aliases")
def list_aliases(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    aliases = [
        AliasRead.model_validate(alias).model_dump()
        for alias in AliasService(db).list_for_item(id_or_code)
    ]
    return ok({"aliases": aliases})


@router.post("/items/{id_or_code}/aliases")
def create_alias(
    id_or_code: str,
    payload: AliasCreate,
    db: Session = Depends(get_db),
) -> dict:
    alias = AliasService(db).create(id_or_code, payload)
    return ok(AliasRead.model_validate(alias).model_dump())


@router.delete("/items/{id_or_code}/aliases/{alias}")
def delete_alias(id_or_code: str, alias: str, db: Session = Depends(get_db)) -> dict:
    AliasService(db).delete(id_or_code, alias)
    return ok({"deleted": True})


@router.post("/items/{id_or_code}/identifiers")
def create_identifier(
    id_or_code: str,
    payload: IdentifierCreate,
    db: Session = Depends(get_db),
) -> dict:
    identifier = IdentifierService(db).create(id_or_code, payload)
    return ok(IdentifierRead.model_validate(identifier).model_dump())


@router.delete("/items/{id_or_code}/identifiers/{identifier_id}")
def delete_identifier(
    id_or_code: str,
    identifier_id: int,
    db: Session = Depends(get_db),
) -> dict:
    IdentifierService(db).delete(id_or_code, identifier_id)
    return ok({"deleted": True})
