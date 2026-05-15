from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.item import Item
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate
from app.services.validators import validate_code


class LocationService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Location]:
        return list(self.db.scalars(select(Location).order_by(Location.full_code)))

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
        has_child = self.db.scalar(select(Location.id).where(Location.parent_id == location.id))
        if has_child:
            raise AppError("LOCATION_NOT_EMPTY", "位置存在子位置，不能删除")
        has_item = self.db.scalar(
            select(Item.id).where(Item.location_id == location.id, Item.is_archived.is_(False))
        )
        if has_item:
            raise AppError("LOCATION_NOT_EMPTY", "位置下还有物品，不能删除")
        self.db.delete(location)
        self.db.commit()


def init_default_location(db: Session) -> None:
    if db.scalar(select(Location).where(Location.full_code == "WS")):
        return
    LocationService(db).create(LocationCreate(name="工坊", code="WS", type="room"))
