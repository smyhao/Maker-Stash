from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.item import (
    ItemCreate,
    ItemMove,
    ItemRead,
    ItemUpdate,
    NoteCreate,
    QuantityAdd,
    QuantityAdjust,
)
from app.services.item_service import ItemService

router = APIRouter(prefix="/items", tags=["items"])


@router.get("")
def list_items(
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
    db: Session = Depends(get_db),
) -> dict:
    bounded_page_size = min(max(page_size, 1), 100)
    service = ItemService(db)
    items = service.list(
        q,
        category,
        location,
        tag,
        status,
        need_restock,
        favorite,
        include_archived,
        page=max(page, 1),
        page_size=bounded_page_size,
    )
    data = [ItemRead.model_validate(item).model_dump() for item in items]
    total = service.count(q, category, location, tag, status, need_restock, favorite, include_archived)
    return ok({"items": data, "total": total, "page": max(page, 1), "page_size": bounded_page_size})


@router.post("")
def create_item(payload: ItemCreate, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).create(payload)
    return ok(ItemRead.model_validate(item).model_dump())


@router.get("/{id_or_code}")
def get_item(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).get(id_or_code)
    return ok(ItemRead.model_validate(item).model_dump())


@router.patch("/{id_or_code}")
def update_item(id_or_code: str, payload: ItemUpdate, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).update(id_or_code, payload)
    return ok(ItemRead.model_validate(item).model_dump())


@router.delete("/{id_or_code}")
def delete_item(
    id_or_code: str,
    delete_attachments: bool = Query(False),
    db: Session = Depends(get_db),
) -> dict:
    ItemService(db).archive(id_or_code, delete_attachments=delete_attachments)
    return ok({"archived": True, "attachments_deleted": delete_attachments})


@router.post("/{id_or_code}/move")
def move_item(id_or_code: str, payload: ItemMove, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).move(id_or_code, payload)
    return ok(ItemRead.model_validate(item).model_dump())


@router.post("/{id_or_code}/add")
def add_quantity(id_or_code: str, payload: QuantityAdd, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).add_quantity(id_or_code, payload)
    return ok(ItemRead.model_validate(item).model_dump())


@router.post("/{id_or_code}/use")
def use_quantity(id_or_code: str, payload: QuantityAdd, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).use_quantity(id_or_code, payload)
    return ok(ItemRead.model_validate(item).model_dump())


@router.post("/{id_or_code}/adjust")
def adjust_quantity(id_or_code: str, payload: QuantityAdjust, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).adjust_quantity(id_or_code, payload)
    return ok(ItemRead.model_validate(item).model_dump())


@router.post("/{id_or_code}/mark-restock")
def mark_restock(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).mark_restock(id_or_code, True)
    return ok(ItemRead.model_validate(item).model_dump())


@router.post("/{id_or_code}/unmark-restock")
def unmark_restock(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).mark_restock(id_or_code, False)
    return ok(ItemRead.model_validate(item).model_dump())


@router.post("/{id_or_code}/favorite")
def favorite(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).favorite(id_or_code, True)
    return ok(ItemRead.model_validate(item).model_dump())


@router.post("/{id_or_code}/unfavorite")
def unfavorite(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    item = ItemService(db).favorite(id_or_code, False)
    return ok(ItemRead.model_validate(item).model_dump())


@router.get("/{id_or_code}/notes")
def list_notes(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    notes = ItemService(db).notes(id_or_code)
    return ok({"notes": [
        {
            "id": note.id,
            "content": note.content,
            "note_type": note.note_type,
            "quantity_change": str(note.quantity_change) if note.quantity_change is not None else None,
            "quantity_after": str(note.quantity_after) if note.quantity_after is not None else None,
            "source": note.source,
            "operator": note.operator,
            "metadata_json": note.metadata_json,
            "created_at": note.created_at,
        }
        for note in notes
    ]})


@router.post("/{id_or_code}/notes")
def add_note(id_or_code: str, payload: NoteCreate, db: Session = Depends(get_db)) -> dict:
    note = ItemService(db).add_note(id_or_code, payload)
    return ok({"id": note.id, "content": note.content})
