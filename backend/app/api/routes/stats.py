from sqlalchemy import func, select
from sqlalchemy.orm import Session, aliased
from fastapi import APIRouter, Depends

from app.core.database import get_db
from app.core.response import ok
from app.models.attachment import Attachment
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview")
def overview(db: Session = Depends(get_db)) -> dict:
    active_filter = Item.is_archived.is_(False)

    item_count = db.scalar(select(func.count()).select_from(Item).where(active_filter)) or 0
    archived_item_count = db.scalar(select(func.count()).select_from(Item).where(Item.is_archived.is_(True))) or 0
    low_stock_count = db.scalar(select(func.count()).select_from(Item).where(active_filter, Item.status == "low")) or 0
    restock_count = db.scalar(select(func.count()).select_from(Item).where(active_filter, Item.need_restock.is_(True))) or 0
    favorite_count = db.scalar(select(func.count()).select_from(Item).where(active_filter, Item.is_favorite.is_(True))) or 0
    unlocated_count = db.scalar(select(func.count()).select_from(Item).where(active_filter, Item.location_id.is_(None))) or 0
    uncategorized_count = db.scalar(select(func.count()).select_from(Item).where(active_filter, Item.category_id.is_(None))) or 0
    attachment_count = (
        db.scalar(
            select(func.count())
            .select_from(Attachment)
            .join(Item, Item.id == Attachment.item_id)
            .where(Item.is_archived.is_(False), Attachment.is_deleted.is_(False))
        )
        or 0
    )

    category_rows = db.execute(
        select(Category.id, Category.name, func.count(Item.id))
        .outerjoin(Item, (Item.category_id == Category.id) & (Item.is_archived.is_(False)))
        .group_by(Category.id, Category.name)
        .order_by(Category.sort_order, Category.id)
    ).all()
    category_parent_rows = db.execute(select(Category.id, Category.parent_id)).all()
    category_parent_by_id = dict(category_parent_rows)
    direct_category_counts = {category_id: count for category_id, _, count in category_rows}
    category_counts = dict(direct_category_counts)
    for category_id, parent_id in category_parent_rows:
        ancestor_id = parent_id
        while ancestor_id is not None:
            category_counts[ancestor_id] = category_counts.get(ancestor_id, 0) + direct_category_counts.get(category_id, 0)
            ancestor_id = category_parent_by_id.get(ancestor_id)

    slot = aliased(Location)
    direct_counts = (
        select(Item.location_id.label("location_id"), func.count(Item.id).label("count"))
        .where(Item.is_archived.is_(False))
        .group_by(Item.location_id)
        .subquery()
    )
    slot_counts = (
        select(slot.parent_id.label("location_id"), func.count(Item.id).label("count"))
        .join(Item, (Item.location_id == slot.id) & (Item.is_archived.is_(False)))
        .where(slot.is_slot.is_(True))
        .group_by(slot.parent_id)
        .subquery()
    )
    location_rows = db.execute(
        select(
            Location.id,
            Location.name,
            Location.full_code,
            (func.coalesce(direct_counts.c.count, 0) + func.coalesce(slot_counts.c.count, 0)).label("count"),
        )
        .outerjoin(direct_counts, direct_counts.c.location_id == Location.id)
        .outerjoin(slot_counts, slot_counts.c.location_id == Location.id)
        .where(Location.is_slot.is_(False))
        .order_by(Location.full_code)
    ).all()

    return ok(
        {
            "item_count": item_count,
            "archived_item_count": archived_item_count,
            "low_stock_count": low_stock_count,
            "restock_count": restock_count,
            "favorite_count": favorite_count,
            "unlocated_count": unlocated_count,
            "uncategorized_count": uncategorized_count,
            "attachment_count": attachment_count,
            "category_counts": [
                {"category_id": category_id, "name": name, "count": category_counts.get(category_id, 0)}
                for category_id, name, _ in category_rows
            ],
            "location_counts": [
                {"location_id": location_id, "name": name, "full_code": full_code, "count": count}
                for location_id, name, full_code, count in location_rows
            ],
        }
    )
