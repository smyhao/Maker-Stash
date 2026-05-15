from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.alias import Alias
from app.models.identifier import Identifier
from app.models.item import Item
from app.models.tag import ItemTag, Tag
from app.schemas.metadata import AliasCreate, IdentifierCreate, TagCreate
from app.services.item_service import ItemService


class TagService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Tag]:
        return list(self.db.scalars(select(Tag).order_by(Tag.name)))

    def get_or_create(self, name: str, slug: str | None = None) -> Tag:
        normalized = name.strip()
        if not normalized:
            raise AppError("VALIDATION_ERROR", "标签名不能为空")
        tag = self.db.scalar(select(Tag).where(Tag.name == normalized))
        if tag:
            return tag
        tag = Tag(name=normalized, slug=slug)
        self.db.add(tag)
        self.db.flush()
        self.db.refresh(tag)
        return tag

    def create(self, payload: TagCreate) -> Tag:
        tag = self.get_or_create(payload.name, payload.slug)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def set_item_tags(self, item: Item, tags: list[str]) -> list[Tag]:
        self.db.execute(delete(ItemTag).where(ItemTag.item_id == item.id))
        result = []
        for name in tags:
            tag = self.get_or_create(name)
            self.db.add(ItemTag(item_id=item.id, tag_id=tag.id))
            result.append(tag)
        return result

    def add_item_tags(self, id_or_code: str, tags: list[str]) -> list[Tag]:
        item = ItemService(self.db).get(id_or_code)
        result = []
        for name in tags:
            tag = self.get_or_create(name)
            exists = self.db.get(ItemTag, {"item_id": item.id, "tag_id": tag.id})
            if not exists:
                self.db.add(ItemTag(item_id=item.id, tag_id=tag.id))
            result.append(tag)
        self.db.commit()
        return result

    def item_tags(self, id_or_code: str) -> list[Tag]:
        item = ItemService(self.db).get(id_or_code)
        return list(
            self.db.scalars(
                select(Tag).join(ItemTag, ItemTag.tag_id == Tag.id).where(ItemTag.item_id == item.id)
            )
        )

    def remove_item_tag(self, id_or_code: str, tag_name: str) -> None:
        item = ItemService(self.db).get(id_or_code)
        tag = self.db.scalar(select(Tag).where(Tag.name == tag_name))
        if not tag:
            return
        self.db.execute(delete(ItemTag).where(ItemTag.item_id == item.id, ItemTag.tag_id == tag.id))
        self.db.commit()

    def delete(self, tag_id: int) -> None:
        tag = self.db.get(Tag, tag_id)
        if tag is None:
            raise NotFoundError("TAG_NOT_FOUND", f"标签不存在：{tag_id}")
        self.db.execute(delete(ItemTag).where(ItemTag.tag_id == tag_id))
        self.db.delete(tag)
        self.db.commit()


class AliasService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_item(self, id_or_code: str) -> list[Alias]:
        item = ItemService(self.db).get(id_or_code)
        return list(self.db.scalars(select(Alias).where(Alias.item_id == item.id).order_by(Alias.alias)))

    def create(self, id_or_code: str, payload: AliasCreate) -> Alias:
        item = ItemService(self.db).get(id_or_code)
        value = payload.alias.strip()
        if not value:
            raise AppError("VALIDATION_ERROR", "别名不能为空")
        alias = self.db.scalar(select(Alias).where(Alias.item_id == item.id, Alias.alias == value))
        if alias:
            return alias
        alias = Alias(item_id=item.id, alias=value)
        self.db.add(alias)
        self.db.commit()
        self.db.refresh(alias)
        return alias

    def delete(self, id_or_code: str, alias_value: str) -> None:
        item = ItemService(self.db).get(id_or_code)
        self.db.execute(delete(Alias).where(Alias.item_id == item.id, Alias.alias == alias_value))
        self.db.commit()


class IdentifierService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, id_or_code: str, payload: IdentifierCreate) -> Identifier:
        item = ItemService(self.db).get(id_or_code)
        exists = self.db.scalar(
            select(Identifier).where(
                Identifier.type == payload.type,
                Identifier.value == payload.value,
            )
        )
        if exists:
            raise AppError("DUPLICATE_CODE", "外部标识已存在")
        identifier = Identifier(
            item_id=item.id,
            type=payload.type,
            value=payload.value,
            description=payload.description,
        )
        self.db.add(identifier)
        self.db.commit()
        self.db.refresh(identifier)
        return identifier

    def find_item(self, value: str) -> Item:
        identifier = self.db.scalar(select(Identifier).where(Identifier.value == value))
        if identifier is None:
            raise NotFoundError("ITEM_NOT_FOUND", f"未找到外部标识：{value}")
        item = self.db.get(Item, identifier.item_id)
        if item is None:
            raise NotFoundError("ITEM_NOT_FOUND", f"物品不存在：{value}")
        return item

    def delete(self, id_or_code: str, identifier_id: int) -> None:
        item = ItemService(self.db).get(id_or_code)
        self.db.execute(
            delete(Identifier).where(
                Identifier.item_id == item.id,
                Identifier.id == identifier_id,
            )
        )
        self.db.commit()
