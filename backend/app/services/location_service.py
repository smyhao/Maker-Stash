from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.item import Item
from app.models.location import Location
from app.models.note import Note
from app.schemas.location import (
    ContainerConvert,
    ContainerCreate,
    ContainerLayout,
    ContainerUpdate,
    LocationCreate,
    LocationUpdate,
    SlotSwap,
)
from app.services.audit_service import AuditService, WriteContext
from app.services.validators import validate_code


class LocationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self, *, include_slots: bool = False) -> list[Location]:
        stmt = select(Location)
        if not include_slots:
            stmt = stmt.where(Location.is_slot.is_(False))
        return list(self.db.scalars(stmt.order_by(Location.full_code)))

    def tree(self) -> list[dict]:
        locations = self.list()
        nodes = [
            {
                "id": location.id,
                "name": location.name,
                "code": location.code,
                "full_code": location.full_code,
                "parent_id": location.parent_id,
                "type": location.type,
                "description": location.description,
                "sort_order": location.sort_order,
                "layout_type": location.layout_type,
                "layout_rows": location.layout_rows,
                "layout_columns": location.layout_columns,
                "appearance_color": location.appearance_color,
                "appearance_icon": location.appearance_icon,
                "is_slot": location.is_slot,
                "slot_key": location.slot_key,
                "slot_order": location.slot_order,
                "created_at": location.created_at,
                "updated_at": location.updated_at,
                "children": [],
            }
            for location in locations
        ]
        by_id = {node["id"]: node for node in nodes}
        roots = []
        for node in nodes:
            parent_id = node["parent_id"]
            parent = by_id.get(parent_id)
            if parent:
                parent["children"].append(node)
            else:
                roots.append(node)
        return roots

    def get(self, location_id: int) -> Location:
        location = self.db.get(Location, location_id)
        if location is None:
            raise NotFoundError("LOCATION_NOT_FOUND", "位置不存在")
        return location

    def get_by_code(self, full_code: str) -> Location:
        location = self.db.scalar(select(Location).where(Location.full_code == full_code))
        if location is None:
            raise NotFoundError("LOCATION_NOT_FOUND", f"位置不存在：{full_code}")
        return location

    def create(self, payload: LocationCreate) -> Location:
        validate_code(payload.code)
        parent = self.get_by_code(payload.parent_code) if payload.parent_code else None
        self._ensure_can_have_children(parent)
        full_code = f"{parent.full_code}.{payload.code}" if parent else payload.code
        if self.db.scalar(select(Location).where(Location.full_code == full_code)):
            raise AppError("LOCATION_CODE_EXISTS", f"位置编号已存在：{full_code}")
        location = Location(
            name=payload.name,
            code=payload.code,
            full_code=full_code,
            parent_id=parent.id if parent else None,
            type=payload.type,
            description=payload.description,
            sort_order=payload.sort_order,
        )
        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)
        return location

    def create_container(self, payload: ContainerCreate) -> Location:
        validate_code(payload.code)
        parent = self.get_by_code(payload.parent_code) if payload.parent_code else None
        self._ensure_can_have_children(parent)
        full_code = f"{parent.full_code}.{payload.code}" if parent else payload.code
        if self.db.scalar(select(Location).where(Location.full_code == full_code)):
            raise AppError("LOCATION_CODE_EXISTS", f"位置编号已存在：{full_code}")
        location = Location(
            name=payload.name,
            code=payload.code,
            full_code=full_code,
            parent_id=parent.id if parent else None,
            type=payload.type,
            description=payload.description,
            sort_order=payload.sort_order,
        )
        self.db.add(location)
        self.db.flush()
        self._apply_layout(location, payload)
        self._create_slots(location, payload)
        self.db.commit()
        self.db.refresh(location)
        return location

    def convert_to_container(self, location_id: int, payload: ContainerConvert) -> Location:
        location = self.get(location_id)
        if location.is_slot:
            raise AppError("SLOT_CANNOT_BECOME_CONTAINER", "格位不能配置为收纳盒")
        if location.layout_type:
            raise AppError("LOCATION_ALREADY_CONTAINER", "该位置已配置为收纳盒")
        if self.db.scalar(select(Location.id).where(Location.parent_id == location.id)):
            raise AppError("LOCATION_HAS_CHILDREN", "存在子位置的节点不能直接配置为收纳盒")
        items = list(
            self.db.scalars(
                select(Item).where(Item.location_id == location.id, Item.is_archived.is_(False))
            )
        )
        assignments = {assignment.item_code: assignment.slot_key for assignment in payload.assignments}
        expected_codes = {item.code for item in items}
        if set(assignments) != expected_codes:
            raise AppError("CONTAINER_ASSIGNMENTS_REQUIRED", "请先为当前位置中的全部物品分配格位")
        if len(set(assignments.values())) != len(assignments):
            raise AppError("SLOT_OCCUPIED", "每个格位只能放置一种物品")
        self._apply_layout(location, payload)
        slots = self._create_slots(location, payload)
        slots_by_key = {slot.slot_key: slot for slot in slots}
        if any(slot_key not in slots_by_key for slot_key in assignments.values()):
            raise AppError("SLOT_NOT_FOUND", "分配目标格位不存在")
        for item in items:
            item.location_id = slots_by_key[assignments[item.code]].id
            self._add_move_note(item, f"配置收纳盒，分配到 {assignments[item.code]}")
        self.db.commit()
        self.db.refresh(location)
        return location

    def update_container(self, location_id: int, payload: ContainerUpdate) -> Location:
        location = self.get(location_id)
        self._ensure_container(location)
        old_slots = list(
            self.db.scalars(
                select(Location).where(Location.parent_id == location.id, Location.is_slot.is_(True))
            )
        )
        desired_keys = set(self._slot_keys(payload))
        removable = [slot for slot in old_slots if slot.slot_key not in desired_keys]
        occupied = self.db.scalar(
            select(Item.id).where(
                Item.location_id.in_([slot.id for slot in removable] or [-1]),
                Item.is_archived.is_(False),
            )
        )
        if occupied:
            raise AppError("CONTAINER_RESIZE_OCCUPIED", "被移除的格位仍有物品，请先完成整理")
        for slot in removable:
            self.db.delete(slot)
        existing_keys = {slot.slot_key for slot in old_slots}
        self._apply_layout(location, payload)
        self._create_slots(location, payload, skip_keys=existing_keys)
        self.db.commit()
        self.db.refresh(location)
        return location

    def board(self, location_id: int) -> dict:
        container = self.get(location_id)
        self._ensure_container(container)
        slots = list(
            self.db.scalars(
                select(Location)
                .where(Location.parent_id == container.id, Location.is_slot.is_(True))
                .order_by(Location.slot_order)
            )
        )
        occupied_items = list(
            self.db.scalars(
                select(Item).where(
                    Item.location_id.in_([slot.id for slot in slots] or [-1]),
                    Item.is_archived.is_(False),
                )
            )
        )
        item_by_location = {item.location_id: item for item in occupied_items}
        return {
            "container": container,
            "slots": [{"location": slot, "item": item_by_location.get(slot.id)} for slot in slots],
        }

    def resolve_msloc(self, code: str) -> dict:
        text = code.strip()
        prefix = "MSLOC:"
        if not text.startswith(prefix):
            raise AppError("INVALID_MSLOC_CODE", "位置二维码内容必须以 MSLOC: 开头")
        full_code = text[len(prefix):].strip()
        if not full_code:
            raise AppError("INVALID_MSLOC_CODE", "位置二维码缺少位置编号")

        location = self.get_by_code(full_code)
        if location.is_slot:
            if location.parent_id is None:
                raise AppError("LOCATION_NOT_CONTAINER", "格位缺少所属收纳盒")
            board = self.board(location.parent_id)
            slot = next(
                (entry for entry in board["slots"] if entry["location"].id == location.id),
                None,
            )
            return {
                "kind": "slot",
                "full_code": full_code,
                "location": location,
                "container": board["container"],
                "slot": slot,
            }

        if location.layout_type:
            board = self.board(location.id)
            return {
                "kind": "container",
                "full_code": full_code,
                "location": location,
                "container": board["container"],
                "slots": board["slots"],
            }

        items = list(
            self.db.scalars(
                select(Item)
                .where(Item.location_id == location.id, Item.is_archived.is_(False))
                .order_by(Item.updated_at.desc(), Item.id.desc())
            )
        )
        return {
            "kind": "location",
            "full_code": full_code,
            "location": location,
            "items": items,
        }

    def ensure_slot_available(self, location: Location, *, item_id: int | None = None) -> None:
        if not location.is_slot:
            return
        stmt = select(Item.id).where(Item.location_id == location.id, Item.is_archived.is_(False))
        if item_id is not None:
            stmt = stmt.where(Item.id != item_id)
        if self.db.scalar(stmt):
            raise AppError("SLOT_OCCUPIED", "目标格位已有物品，请使用交换操作")

    def swap_slots(self, container_id: int, payload: SlotSwap) -> tuple[Item, Item]:
        container = self.get(container_id)
        self._ensure_container(container)
        source = self.db.scalar(select(Item).where(Item.code == payload.source_item_code))
        if source is None:
            raise NotFoundError("ITEM_NOT_FOUND", f"物品不存在：{payload.source_item_code}")
        if source.is_archived:
            raise AppError("ARCHIVED_ITEM_MOVE_FORBIDDEN", "物品已归档，不能移动位置")
        source_slot = self.db.get(Location, source.location_id) if source.location_id else None
        if source_slot is None or source_slot.parent_id != container.id or not source_slot.is_slot:
            raise AppError("SOURCE_NOT_IN_CONTAINER", "来源物品不在当前收纳盒格位内")
        target_slot = self.db.scalar(
            select(Location).where(
                Location.parent_id == container.id,
                Location.is_slot.is_(True),
                Location.slot_key == payload.target_slot_key,
            )
        )
        if target_slot is None:
            raise NotFoundError("SLOT_NOT_FOUND", "目标格位不存在")
        target = self.db.scalar(
            select(Item).where(Item.location_id == target_slot.id, Item.is_archived.is_(False))
        )
        if target is None:
            raise AppError("TARGET_SLOT_EMPTY", "空格位请使用移动操作")
        if target.id == source.id:
            raise AppError("SAME_SLOT", "来源与目标格位相同")
        before_source = self._item_snapshot(source)
        before_target = self._item_snapshot(target)
        source.location_id, target.location_id = target_slot.id, source_slot.id
        ctx = WriteContext.from_payload(payload)
        self._add_move_note(source, f"与 {target.name} 交换格位至 {target_slot.slot_key}", ctx)
        self._add_move_note(target, f"与 {source.name} 交换格位至 {source_slot.slot_key}", ctx)
        audit = AuditService(self.db)
        audit.record(ctx, action="item.slot.swap", target_type="item", target_id=source.id, before=before_source, after=self._item_snapshot(source))
        audit.record(ctx, action="item.slot.swap", target_type="item", target_id=target.id, before=before_target, after=self._item_snapshot(target))
        self.db.commit()
        self.db.refresh(source)
        self.db.refresh(target)
        return source, target

    def update(self, location_id: int, payload: LocationUpdate) -> Location:
        location = self.get(location_id)
        # code/full_code deliberately stay immutable in v1 to protect external bindings.
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(location, key, value)
        self.db.commit()
        self.db.refresh(location)
        return location

    def delete(self, location_id: int) -> None:
        location = self.get(location_id)
        children = list(self.db.scalars(select(Location).where(Location.parent_id == location.id)))
        if children and (not location.layout_type or any(not child.is_slot for child in children)):
            raise AppError("LOCATION_NOT_EMPTY", "位置存在子位置，不能删除")
        child_ids = [child.id for child in children]
        delete_location_ids = [location.id, *child_ids]
        has_slot_item = self.db.scalar(
            select(Item.id).where(
                Item.location_id.in_(child_ids or [-1]),
                Item.is_archived.is_(False),
            )
        )
        if has_slot_item:
            raise AppError("LOCATION_NOT_EMPTY", "收纳盒格位下还有物品，不能删除")
        has_item = self.db.scalar(
            select(Item.id).where(Item.location_id == location.id, Item.is_archived.is_(False))
        )
        if has_item:
            raise AppError("LOCATION_NOT_EMPTY", "位置下还有物品，不能删除")
        self.db.execute(
            update(Item)
            .where(Item.location_id.in_(delete_location_ids), Item.is_archived.is_(True))
            .values(location_id=None)
        )
        for child in children:
            self.db.delete(child)
        self.db.flush()
        self.db.delete(location)
        self.db.commit()

    def _ensure_container(self, location: Location) -> None:
        if not location.layout_type or location.is_slot:
            raise AppError("LOCATION_NOT_CONTAINER", "该位置不是可视化收纳盒")

    def _ensure_can_have_children(self, location: Location | None) -> None:
        if location and (location.layout_type or location.is_slot):
            raise AppError("CONTAINER_CHILD_FORBIDDEN", "收纳盒和格位不能再创建子位置")

    def _apply_layout(self, location: Location, payload: ContainerLayout) -> None:
        location.layout_type = payload.layout_type
        location.layout_rows = payload.layout_rows
        location.layout_columns = payload.layout_columns
        location.appearance_color = payload.appearance_color
        location.appearance_icon = payload.appearance_icon

    def _slot_keys(self, payload: ContainerLayout) -> list[str]:
        if payload.layout_type == "row":
            return [f"{column:02d}" for column in range(1, payload.layout_columns + 1)]
        return [
            f"{chr(64 + row)}{column:02d}"
            for row in range(1, payload.layout_rows + 1)
            for column in range(1, payload.layout_columns + 1)
        ]

    def _create_slots(
        self,
        container: Location,
        payload: ContainerLayout,
        *,
        skip_keys: set[str] | None = None,
    ) -> list[Location]:
        slots = []
        skip_keys = skip_keys or set()
        for order, slot_key in enumerate(self._slot_keys(payload), start=1):
            if slot_key in skip_keys:
                continue
            slot = Location(
                name=slot_key,
                code=slot_key,
                full_code=f"{container.full_code}.{slot_key}",
                parent_id=container.id,
                type="slot",
                description=None,
                sort_order=order,
                is_slot=True,
                slot_key=slot_key,
                slot_order=order,
            )
            self.db.add(slot)
            slots.append(slot)
        self.db.flush()
        return slots

    def _add_move_note(self, item: Item, content: str, ctx: WriteContext | None = None) -> None:
        context = ctx or WriteContext(source="web", module="locations")
        self.db.add(
            Note(
                item_id=item.id,
                note_type="move",
                content=content,
                source=context.source,
                operator=context.operator,
            )
        )

    def _item_snapshot(self, item: Item) -> dict:
        return {"id": item.id, "code": item.code, "location_id": item.location_id}


def init_default_location(db: Session) -> None:
    if db.scalar(select(Location).where(Location.full_code == "WS")):
        return
    LocationService(db).create(LocationCreate(name="工坊", code="WS", type="room"))
