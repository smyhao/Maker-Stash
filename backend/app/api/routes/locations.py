from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.location import (
    ContainerConvert,
    ContainerCreate,
    ContainerUpdate,
    LocationCreate,
    LocationRead,
    LocationTreeNode,
    LocationUpdate,
    SlotSwap,
)
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


@router.post("/containers")
def create_container(payload: ContainerCreate, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).create_container(payload)
    return ok(LocationRead.model_validate(location).model_dump())


@router.post("/{location_id}/container")
def convert_to_container(location_id: int, payload: ContainerConvert, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).convert_to_container(location_id, payload)
    return ok(LocationRead.model_validate(location).model_dump())


@router.patch("/{location_id}/container")
def update_container(location_id: int, payload: ContainerUpdate, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).update_container(location_id, payload)
    return ok(LocationRead.model_validate(location).model_dump())


@router.get("/{location_id}/board")
def container_board(location_id: int, db: Session = Depends(get_db)) -> dict:
    board = LocationService(db).board(location_id)
    return ok(
        {
            "container": LocationRead.model_validate(board["container"]).model_dump(),
            "slots": [
                {
                    "location": LocationRead.model_validate(slot["location"]).model_dump(),
                    "item": ItemRead.model_validate(slot["item"]).model_dump() if slot["item"] else None,
                }
                for slot in board["slots"]
            ],
        }
    )


@router.post("/{location_id}/swap")
def swap_container_slots(location_id: int, payload: SlotSwap, db: Session = Depends(get_db)) -> dict:
    source, target = LocationService(db).swap_slots(location_id, payload)
    return ok(
        {
            "items": [
                ItemRead.model_validate(source).model_dump(),
                ItemRead.model_validate(target).model_dump(),
            ]
        }
    )


@router.get("/resolve-msloc")
def resolve_msloc(code: str, db: Session = Depends(get_db)) -> dict:
    resolved = LocationService(db).resolve_msloc(code)
    data = {
        "kind": resolved["kind"],
        "full_code": resolved["full_code"],
        "location": LocationRead.model_validate(resolved["location"]).model_dump(),
    }
    if resolved["kind"] == "slot":
        data["container"] = LocationRead.model_validate(resolved["container"]).model_dump()
        data["slot"] = {
            "location": LocationRead.model_validate(resolved["slot"]["location"]).model_dump(),
            "item": ItemRead.model_validate(resolved["slot"]["item"]).model_dump() if resolved["slot"]["item"] else None,
        }
    elif resolved["kind"] == "container":
        data["container"] = LocationRead.model_validate(resolved["container"]).model_dump()
        data["slots"] = [
            {
                "location": LocationRead.model_validate(slot["location"]).model_dump(),
                "item": ItemRead.model_validate(slot["item"]).model_dump() if slot["item"] else None,
            }
            for slot in resolved["slots"]
        ]
    else:
        data["items"] = [ItemRead.model_validate(item).model_dump() for item in resolved["items"]]
    return ok(data)


@router.get("/by-code/{full_code}")
def get_location_by_code(full_code: str, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).get_by_code(full_code)
    return ok(LocationRead.model_validate(location).model_dump())


@router.get("/by-code/{full_code}/items")
def get_location_items(full_code: str, db: Session = Depends(get_db)) -> dict:
    items = ItemService(db).list(location=full_code, page_size=10000)
    data = [ItemRead.model_validate(item).model_dump() for item in items]
    return ok({"items": data})


@router.get("/{location_id}")
def get_location(location_id: int, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).get(location_id)
    return ok(LocationRead.model_validate(location).model_dump())


@router.get("/{location_id}/items")
def get_location_items_by_id(location_id: int, db: Session = Depends(get_db)) -> dict:
    location = LocationService(db).get(location_id)
    items = ItemService(db).list(location=location.full_code, page_size=10000)
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
