from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.alias import Alias
from app.models.attachment import Attachment
from app.models.attribute import ItemAttributeValue
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location
from app.models.note import Note
from app.models.tag import ItemTag, Tag


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(self, q: str, limit: int = 20, include_archived: bool = False) -> list[dict]:
        like = f"%{q}%"
        stmt = (
            select(Item)
            .outerjoin(Category, Item.category_id == Category.id)
            .outerjoin(Location, Item.location_id == Location.id)
            .where(
                or_(
                    Item.name.like(like),
                    Item.code.like(like),
                    Item.description.like(like),
                    Category.name.like(like),
                    Category.slug.like(like),
                    Location.full_code.like(like),
                    Location.name.like(like),
                    Item.id.in_(select(Alias.item_id).where(Alias.alias.like(like))),
                    Item.id.in_(
                        select(ItemTag.item_id)
                        .join(Tag, Tag.id == ItemTag.tag_id)
                        .where(Tag.name.like(like))
                    ),
                    Item.id.in_(select(Note.item_id).where(Note.content.like(like))),
                    Item.id.in_(
                        select(ItemAttributeValue.item_id).where(
                            or_(
                                ItemAttributeValue.name.like(like),
                                ItemAttributeValue.value.like(like),
                            )
                        )
                    ),
                    Item.id.in_(
                        select(Attachment.item_id).where(
                            Attachment.original_name.like(like),
                            Attachment.is_deleted.is_(False),
                        )
                    ),
                )
            )
            .limit(limit)
        )
        if not include_archived:
            stmt = stmt.where(Item.is_archived.is_(False))
        items = self.db.scalars(stmt).unique().all()
        return [self._to_result(item, q) for item in items]

    def _to_result(self, item: Item, q: str) -> dict:
        matched_by = []
        q_lower = q.lower()
        if q_lower in item.name.lower():
            matched_by.append("name")
        if q_lower in item.code.lower():
            matched_by.append("code")
        return {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "category_id": item.category_id,
            "location_id": item.location_id,
            "quantity": str(item.quantity) if item.quantity is not None else None,
            "unit": item.unit,
            "status": item.status,
            "cover_attachment_id": item.cover_attachment_id,
            "matched_by": matched_by or ["related"],
        }
