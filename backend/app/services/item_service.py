from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.attribute import ItemAttributeValue
from app.models.attachment import Attachment
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.note import Note
from app.models.tag import ItemTag, Tag
from app.schemas.item import ItemCreate, ItemMove, ItemUpdate, NoteCreate, QuantityAdd, QuantityAdjust
from app.services.category_service import CategoryService
from app.services.location_service import LocationService
from app.services.search_service import fulltext_where


class ItemService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        q: str | None = None,
        category: str | None = None,
        location: str | None = None,
        tag: str | None = None,
        status: str | None = None,
        need_restock: bool | None = None,
        favorite: bool | None = None,
        include_archived: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> list[Item]:
        stmt = self._list_stmt(q, category, location, tag, status, need_restock, favorite, include_archived)
        offset = (max(page, 1) - 1) * page_size
        return list(
            self.db.scalars(
                stmt.order_by(Item.updated_at.desc(), Item.id.desc()).offset(offset).limit(page_size)
            )
        )

    def count(
        self,
        q: str | None = None,
        category: str | None = None,
        location: str | None = None,
        tag: str | None = None,
        status: str | None = None,
        need_restock: bool | None = None,
        favorite: bool | None = None,
        include_archived: bool = False,
    ) -> int:
        stmt = self._list_stmt(q, category, location, tag, status, need_restock, favorite, include_archived)
        return self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    def _list_stmt(
        self,
        q: str | None,
        category: str | None,
        location: str | None,
        tag: str | None,
        status: str | None,
        need_restock: bool | None,
        favorite: bool | None,
        include_archived: bool,
    ):
        stmt = select(Item)
        if not include_archived:
            stmt = stmt.where(Item.is_archived.is_(False))
        if q:
            like = f"%{q}%"
            stmt = stmt.where(fulltext_where(Item, like))
        if category:
            found = CategoryService(self.db).find_by_any(category)
            if found:
                stmt = stmt.where(Item.category_id == found.id)
        if location:
            found_location = LocationService(self.db).get_by_code(location)
            stmt = stmt.where(Item.location_id == found_location.id)
        if tag:
            stmt = stmt.where(
                Item.id.in_(
                    select(ItemTag.item_id)
                    .join(Tag, Tag.id == ItemTag.tag_id)
                    .where(Tag.name == tag)
                )
            )
        if status:
            stmt = stmt.where(Item.status == status)
        if need_restock is not None:
            stmt = stmt.where(Item.need_restock.is_(need_restock))
        if favorite is not None:
            stmt = stmt.where(Item.is_favorite.is_(favorite))
        return stmt

    def get(self, id_or_code: str) -> Item:
        item = None
        if id_or_code.isdigit():
            item = self.db.get(Item, int(id_or_code))
        if item is None:
            item = self.db.scalar(select(Item).where(Item.code == id_or_code))
        if item is None:
            raise NotFoundError("ITEM_NOT_FOUND", f"物品不存在：{id_or_code}")
        return item

    def create(self, payload: ItemCreate) -> Item:
        category = CategoryService(self.db).find_by_any(payload.category)
        location = (
            LocationService(self.db).get_by_code(payload.location_code)
            if payload.location_code
            else None
        )
        code = self._next_code(category)
        item = Item(
            code=code,
            name=payload.name,
            category_id=category.id if category else None,
            location_id=location.id if location else None,
            location_text=payload.location_text,
            quantity=payload.quantity,
            unit=payload.unit,
            status=payload.status,
            description=payload.description,
        )
        self.db.add(item)
        self.db.flush()
        for attr in payload.attributes:
            self.db.add(
                ItemAttributeValue(
                    item_id=item.id,
                    name=attr.name,
                    key=attr.key,
                    value=attr.value,
                    value_type=attr.value_type,
                    unit=attr.unit,
                )
            )
        if payload.note:
            self._add_note(item, "note", payload.note, source="api")
        if payload.tags:
            from app.services.metadata_service import TagService

            TagService(self.db).set_item_tags(item, payload.tags)
        self.db.commit()
        self.db.refresh(item)
        return item

    def update(self, id_or_code: str, payload: ItemUpdate) -> Item:
        item = self.get(id_or_code)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        self._add_note(item, "status", "修改物品基础信息", source="api")
        self.db.commit()
        self.db.refresh(item)
        return item

    def archive(self, id_or_code: str, delete_attachments: bool = False) -> None:
        item = self.get(id_or_code)
        item.is_archived = True
        item.status = "archived"
        self._add_note(item, "system", "归档物品", source="api")
        if delete_attachments:
            attachments = self.db.scalars(
                select(Attachment).where(Attachment.item_id == item.id)
            ).all()
            for attachment in attachments:
                attachment.is_deleted = True
        self.db.commit()

    def move(self, id_or_code: str, payload: ItemMove) -> Item:
        item = self.get(id_or_code)
        location = (
            LocationService(self.db).get_by_code(payload.location_code)
            if payload.location_code
            else None
        )
        item.location_id = location.id if location else None
        item.location_text = payload.location_text
        self._add_note(item, "move", payload.note or "移动位置", source=payload.source)
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_quantity(self, id_or_code: str, payload: QuantityAdd) -> Item:
        item = self.get(id_or_code)
        current = item.quantity or Decimal("0")
        item.quantity = current + payload.amount
        if payload.unit:
            item.unit = payload.unit
        self._add_note(item, "add", payload.note or "增加数量", payload.amount, item.quantity, payload.source)
        self.db.commit()
        self.db.refresh(item)
        return item

    def use_quantity(self, id_or_code: str, payload: QuantityAdd) -> Item:
        item = self.get(id_or_code)
        current = item.quantity or Decimal("0")
        item.quantity = current - payload.amount
        if payload.unit:
            item.unit = payload.unit
        self._add_note(item, "use", payload.note or "使用物品", -payload.amount, item.quantity, payload.source)
        self.db.commit()
        self.db.refresh(item)
        return item

    def adjust_quantity(self, id_or_code: str, payload: QuantityAdjust) -> Item:
        item = self.get(id_or_code)
        before = item.quantity or Decimal("0")
        item.quantity = payload.quantity
        if payload.unit:
            item.unit = payload.unit
        self._add_note(item, "adjust", payload.note or "调整数量", payload.quantity - before, item.quantity, payload.source)
        self.db.commit()
        self.db.refresh(item)
        return item

    def mark_restock(self, id_or_code: str, value: bool) -> Item:
        item = self.get(id_or_code)
        item.need_restock = value
        self._add_note(item, "restock", "标记补货" if value else "取消补货标记", source="api")
        self.db.commit()
        self.db.refresh(item)
        return item

    def favorite(self, id_or_code: str, value: bool) -> Item:
        item = self.get(id_or_code)
        item.is_favorite = value
        self.db.commit()
        self.db.refresh(item)
        return item

    def add_note(self, id_or_code: str, payload: NoteCreate) -> Note:
        item = self.get(id_or_code)
        note = self._add_note(
            item,
            payload.note_type,
            payload.content,
            source=payload.source,
            operator=payload.operator,
            metadata_json=payload.metadata_json,
        )
        self.db.commit()
        self.db.refresh(note)
        return note

    def notes(self, id_or_code: str) -> list[Note]:
        item = self.get(id_or_code)
        return list(self.db.scalars(select(Note).where(Note.item_id == item.id).order_by(Note.created_at.desc())))

    def _next_code(self, category: Category | None) -> str:
        prefix = category.code_prefix if category else "OTH"
        current = self.db.scalar(
            select(func.max(Item.code)).where(Item.code.like(f"{prefix}-%"))
        )
        next_number = int(current.split("-")[-1]) + 1 if current else 1
        return f"{prefix}-{next_number:06d}"

    def _add_note(
        self,
        item: Item,
        note_type: str,
        content: str,
        quantity_change: Decimal | None = None,
        quantity_after: Decimal | None = None,
        source: str = "api",
        operator: str | None = None,
        metadata_json: str | None = None,
    ) -> Note:
        note = Note(
            item_id=item.id,
            note_type=note_type,
            content=content,
            quantity_change=quantity_change,
            quantity_after=quantity_after,
            source=source,
            operator=operator,
            metadata_json=metadata_json,
        )
        self.db.add(note)
        return note
