from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
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
from app.services.audit_service import AuditService, IdempotencyService, WriteContext
from app.services.category_service import CategoryService
from app.services.file_storage import delete_upload_relative_file
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
            category_service = CategoryService(self.db)
            found = category_service.find_by_any(category)
            if found:
                stmt = stmt.where(Item.category_id.in_(category_service.branch_ids(found)))
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

    def create(self, payload: ItemCreate, *, commit: bool = True) -> Item:
        ctx = WriteContext.from_payload(payload)
        idempotency = IdempotencyService(self.db)
        existing = idempotency.get_existing(ctx, "item.create")
        if existing:
            return self._get_item_by_id(existing.target_id)
        category = CategoryService(self.db).find_by_any(payload.category)
        if payload.category is not None and category is None:
            raise NotFoundError("CATEGORY_NOT_FOUND", f"分类不存在：{payload.category}")
        location = (
            LocationService(self.db).get_by_code(payload.location_code)
            if payload.location_code
            else None
        )
        if location:
            LocationService(self.db).ensure_slot_available(location)
        last_error: IntegrityError | None = None
        for _ in range(3):
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
            try:
                self.db.flush()
            except IntegrityError as exc:
                self.db.rollback()
                last_error = exc
                continue
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
                self._add_note(item, "note", payload.note, source=ctx.source, operator=ctx.operator)
            if payload.tags:
                from app.services.metadata_service import TagService

                TagService(self.db).set_item_tags(item, payload.tags)
            AuditService(self.db).record(
                ctx,
                action="item.create",
                target_type="item",
                target_id=item.id,
                before=None,
                after=self._item_snapshot(item),
            )
            idempotency.remember(ctx, "item.create", "item", item.id)
            self._finish_write(item, commit)
            return item
        raise AppError("DUPLICATE_CODE", "物品编号冲突，请重试") from last_error

    def update(self, id_or_code: str, payload: ItemUpdate, *, commit: bool = True) -> Item:
        ctx = WriteContext.from_payload(payload)
        idempotency = IdempotencyService(self.db)
        existing = idempotency.get_existing(ctx, "item.update")
        if existing:
            return self._get_item_by_id(existing.target_id)
        item = self.get(id_or_code)
        before = self._item_snapshot(item)
        data = payload.model_dump(exclude_unset=True)
        data.pop("source", None)
        data.pop("module", None)
        data.pop("operator", None)
        data.pop("request_id", None)
        self._ensure_archived_update_allowed(item, data)
        if "category_id" in data and data["category_id"] is not None:
            CategoryService(self.db).get(data["category_id"])
        if "location_id" in data and data["location_id"] is not None:
            target_location = LocationService(self.db).get(data["location_id"])
            LocationService(self.db).ensure_slot_available(target_location, item_id=item.id)
        for key, value in data.items():
            setattr(item, key, value)
        self.db.flush()
        self._add_note(item, "status", "修改物品基础信息", source=ctx.source, operator=ctx.operator)
        AuditService(self.db).record(
            ctx,
            action="item.update",
            target_type="item",
            target_id=item.id,
            before=before,
            after=self._item_snapshot(item),
        )
        idempotency.remember(ctx, "item.update", "item", item.id)
        self._finish_write(item, commit)
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
                delete_upload_relative_file(attachment.file_path)
                delete_upload_relative_file(attachment.thumbnail_path)
                attachment.is_deleted = True
                attachment.is_cover = False
            item.cover_attachment_id = None
        self.db.commit()

    def move(self, id_or_code: str, payload: ItemMove, *, commit: bool = True) -> Item:
        ctx = WriteContext.from_payload(payload)
        idempotency = IdempotencyService(self.db)
        existing = idempotency.get_existing(ctx, "item.move")
        if existing:
            return self._get_item_by_id(existing.target_id)
        item = self.get(id_or_code)
        self._ensure_not_archived(item, "ARCHIVED_ITEM_MOVE_FORBIDDEN", "物品已归档，不能移动位置")
        before = self._item_snapshot(item)
        location = (
            LocationService(self.db).get_by_code(payload.location_code)
            if payload.location_code
            else None
        )
        if location:
            LocationService(self.db).ensure_slot_available(location, item_id=item.id)
        item.location_id = location.id if location else None
        item.location_text = payload.location_text
        self.db.flush()
        self._add_note(item, "move", payload.note or "移动位置", source=ctx.source, operator=ctx.operator)
        AuditService(self.db).record(
            ctx,
            action="item.move",
            target_type="item",
            target_id=item.id,
            before=before,
            after=self._item_snapshot(item),
        )
        idempotency.remember(ctx, "item.move", "item", item.id)
        self._finish_write(item, commit)
        return item

    def add_quantity(self, id_or_code: str, payload: QuantityAdd, *, commit: bool = True) -> Item:
        ctx = WriteContext.from_payload(payload)
        idempotency = IdempotencyService(self.db)
        existing = idempotency.get_existing(ctx, "item.quantity.add")
        if existing:
            return self._get_item_by_id(existing.target_id)
        item = self.get(id_or_code)
        self._ensure_not_archived(item, "ARCHIVED_ITEM_QUANTITY_FORBIDDEN", "物品已归档，不能变更库存")
        before = self._item_snapshot(item)
        current = item.quantity or Decimal("0")
        item.quantity = current + payload.amount
        if payload.unit:
            item.unit = payload.unit
        self.db.flush()
        self._add_note(item, "add", payload.note or "增加数量", payload.amount, item.quantity, ctx.source, ctx.operator)
        AuditService(self.db).record(
            ctx,
            action="item.quantity.add",
            target_type="item",
            target_id=item.id,
            before=before,
            after=self._item_snapshot(item),
        )
        idempotency.remember(ctx, "item.quantity.add", "item", item.id)
        self._finish_write(item, commit)
        return item

    def use_quantity(self, id_or_code: str, payload: QuantityAdd, *, commit: bool = True) -> Item:
        ctx = WriteContext.from_payload(payload)
        idempotency = IdempotencyService(self.db)
        existing = idempotency.get_existing(ctx, "item.quantity.use")
        if existing:
            return self._get_item_by_id(existing.target_id)
        item = self.get(id_or_code)
        self._ensure_not_archived(item, "ARCHIVED_ITEM_QUANTITY_FORBIDDEN", "物品已归档，不能变更库存")
        before = self._item_snapshot(item)
        current = item.quantity or Decimal("0")
        next_quantity = current - payload.amount
        self._ensure_non_negative(next_quantity)
        item.quantity = next_quantity
        if payload.unit:
            item.unit = payload.unit
        self.db.flush()
        self._add_note(item, "use", payload.note or "使用物品", -payload.amount, item.quantity, ctx.source, ctx.operator)
        AuditService(self.db).record(
            ctx,
            action="item.quantity.use",
            target_type="item",
            target_id=item.id,
            before=before,
            after=self._item_snapshot(item),
        )
        idempotency.remember(ctx, "item.quantity.use", "item", item.id)
        self._finish_write(item, commit)
        return item

    def adjust_quantity(self, id_or_code: str, payload: QuantityAdjust, *, commit: bool = True) -> Item:
        ctx = WriteContext.from_payload(payload)
        idempotency = IdempotencyService(self.db)
        existing = idempotency.get_existing(ctx, "item.quantity.adjust")
        if existing:
            return self._get_item_by_id(existing.target_id)
        item = self.get(id_or_code)
        self._ensure_not_archived(item, "ARCHIVED_ITEM_QUANTITY_FORBIDDEN", "物品已归档，不能变更库存")
        before_snapshot = self._item_snapshot(item)
        before = item.quantity or Decimal("0")
        item.quantity = payload.quantity
        if payload.unit:
            item.unit = payload.unit
        self.db.flush()
        self._add_note(item, "adjust", payload.note or "调整数量", payload.quantity - before, item.quantity, ctx.source, ctx.operator)
        AuditService(self.db).record(
            ctx,
            action="item.quantity.adjust",
            target_type="item",
            target_id=item.id,
            before=before_snapshot,
            after=self._item_snapshot(item),
        )
        idempotency.remember(ctx, "item.quantity.adjust", "item", item.id)
        self._finish_write(item, commit)
        return item

    def _ensure_not_archived(self, item: Item, code: str, message: str) -> None:
        if item.is_archived:
            raise AppError(code, message)

    def _ensure_archived_update_allowed(self, item: Item, data: dict) -> None:
        if not item.is_archived:
            return
        quantity_fields = {"quantity", "unit"}
        location_fields = {"location_id", "location_text"}
        if any(field in data and data[field] != getattr(item, field) for field in quantity_fields):
            raise AppError("ARCHIVED_ITEM_QUANTITY_FORBIDDEN", "物品已归档，不能变更库存")
        if any(field in data and data[field] != getattr(item, field) for field in location_fields):
            raise AppError("ARCHIVED_ITEM_MOVE_FORBIDDEN", "物品已归档，不能移动位置")

    def _ensure_non_negative(self, quantity: Decimal) -> None:
        if quantity < 0:
            raise AppError("NEGATIVE_QUANTITY_NOT_ALLOWED", "库存不能变为负数")

    def _finish_write(self, item: Item, commit: bool) -> None:
        if commit:
            self.db.commit()
            self.db.refresh(item)
        else:
            self.db.flush()

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

    def _get_item_by_id(self, item_id: str | int) -> Item:
        item = self.db.get(Item, int(item_id))
        if item is None:
            raise NotFoundError("ITEM_NOT_FOUND", f"物品不存在：{item_id}")
        return item

    def _item_snapshot(self, item: Item) -> dict:
        return {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "category_id": item.category_id,
            "location_id": item.location_id,
            "location_text": item.location_text,
            "quantity": str(item.quantity) if item.quantity is not None else None,
            "unit": item.unit,
            "status": item.status,
            "description": item.description,
            "need_restock": item.need_restock,
            "is_favorite": item.is_favorite,
            "is_archived": item.is_archived,
        }

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
