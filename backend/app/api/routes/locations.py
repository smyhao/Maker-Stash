from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.location import LocationCreate, LocationRead, LocationTreeNode, LocationUpdate
from app.schemas.item import ItemRead
from app.services.item_service import ItemService
from app.services.location_service import LocationService

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("")
def list_locations(db: Session = Depends(get_db)) -> dict:
    data = [LocationRead.model_validate(item).model_dump() for item in LocationService(db).list()]
    return ok({"locations": data})


@router.get("/tree")
def location_tree(db: Session = Depends(get_db)) -> dict:
    data = [LocationTreeNode.model_validate(item).model_dump() for item in LocationService(db).tree()]
    return ok({"locations": data})


@router.post("")
def create_location(payload: LocationCreate, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).create(payload)
    return ok(LocationRead.model_validate(location).model_dump())


@router.get("/{location_id}")
def get_location(location_id: int, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).get(location_id)
    return ok(LocationRead.model_validate(location).model_dump())


@router.get("/{location_id}/items")
def get_location_items_by_id(location_id: int, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).get(location_id)
    items = ItemService(db).list(location=location.full_code)
    data = [ItemRead.model_validate(item).model_dump() for item in items]
    return ok({"items": data})


@router.get("/by-code/{full_code}")
def get_location_by_code(full_code: str, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).get_by_code(full_code)
    return ok(LocationRead.model_validate(location).model_dump())


@router.get("/by-code/{full_code}/items")
def get_location_items(full_code: str, db: Session = Depends(get_db)) -> dict:
    items = ItemService(db).list(location=full_code)
    data = [ItemRead.model_validate(item).model_dump() for item in items]
    return ok({"items": data})


@router.patch("/{location_id}")
def update_location(location_id: int, payload: LocationUpdate, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).update(location_id, payload)
    return ok(LocationRead.model_validate(location).model_dump())


@router.delete("/{location_id}")
def delete_location(location_id: int, db: Session = Depends(get_db)) -> dict:
    LocationService(db).delete(location_id)
    return ok({"deleted": True})
