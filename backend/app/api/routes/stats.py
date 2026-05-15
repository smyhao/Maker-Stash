from sqlalchemy import func, select
from sqlalchemy.orm import Session
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

    location_rows = db.execute(
        select(Location.id, Location.name, Location.full_code, func.count(Item.id))
        .outerjoin(Item, (Item.location_id == Location.id) & (Item.is_archived.is_(False)))
        .group_by(Location.id, Location.name, Location.full_code)
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
                {"category_id": category_id, "name": name, "count": count}
                for category_id, name, count in category_rows
            ],
            "location_counts": [
                {"location_id": location_id, "name": name, "full_code": full_code, "count": count}
                for location_id, name, full_code, count in location_rows
            ],
        }
    )
