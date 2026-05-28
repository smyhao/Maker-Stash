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
from app.services.category_service import CategoryService
from app.services.location_service import LocationService


def fulltext_where(Item, like: str):
    """全字段模糊搜索 WHERE 条件，覆盖名称/编号/描述/分类/位置/标签/别名/备注/属性/附件名。"""
    from sqlalchemy import exists

    return or_(
        Item.name.like(like),
        Item.code.like(like),
        Item.description.like(like),
        exists(
            select(Category.id)
            .where(Category.id == Item.category_id, or_(Category.name.like(like), Category.slug.like(like)))
        ),
        exists(
            select(Location.id)
            .where(Location.id == Item.location_id, or_(Location.full_code.like(like), Location.name.like(like)))
        ),
        Item.id.in_(select(Alias.item_id).where(Alias.alias.like(like))),
        Item.id.in_(
            select(ItemTag.item_id)
            .join(Tag, Tag.id == ItemTag.tag_id)
            .where(Tag.name.like(like))
        ),
        Item.id.in_(select(Note.item_id).where(Note.content.like(like))),
        Item.id.in_(
            select(ItemAttributeValue.item_id).where(
                or_(ItemAttributeValue.name.like(like), ItemAttributeValue.value.like(like))
            )
        ),
        Item.id.in_(
            select(Attachment.item_id).where(
                Attachment.original_name.like(like), Attachment.is_deleted.is_(False)
            )
        ),
    )


def compute_matched_by(db: Session, item: Item, q_lower: str) -> list[str]:
    """计算搜索结果具体由哪些维度命中。"""
    matched = []
    if q_lower in item.name.lower():
        matched.append("name")
    if q_lower in item.code.lower():
        matched.append("code")
    if item.description and q_lower in item.description.lower():
        matched.append("description")
    if _hit(db, Alias.item_id, Alias.alias, item.id, q_lower):
        matched.append("alias")
    if _hit_join(db, item.id, q_lower):
        matched.append("tag")
    if _hit_attr(db, item.id, q_lower):
        matched.append("attribute")
    if _hit(db, Note.item_id, Note.content, item.id, q_lower):
        matched.append("note")
    if _hit_attachment(db, item.id, q_lower):
        matched.append("attachment")
    if _hit_category(db, item, q_lower):
        matched.append("category")
    if _hit_location(db, item, q_lower):
        matched.append("location")
    return matched or ["related"]


def _hit(db: Session, col, like_col, item_id: int, q_lower: str) -> bool:
    return db.scalar(select(col).where(col == item_id, like_col.like(f"%{q_lower}%")).limit(1)) is not None


def _hit_join(db: Session, item_id: int, q_lower: str) -> bool:
    return db.scalar(
        select(ItemTag.item_id)
        .join(Tag, Tag.id == ItemTag.tag_id)
        .where(ItemTag.item_id == item_id, Tag.name.like(f"%{q_lower}%"))
        .limit(1)
    ) is not None


def _hit_attr(db: Session, item_id: int, q_lower: str) -> bool:
    return db.scalar(
        select(ItemAttributeValue.id)
        .where(
            ItemAttributeValue.item_id == item_id,
            or_(ItemAttributeValue.name.like(f"%{q_lower}%"), ItemAttributeValue.value.like(f"%{q_lower}%")),
        )
        .limit(1)
    ) is not None


def _hit_attachment(db: Session, item_id: int, q_lower: str) -> bool:
    return db.scalar(
        select(Attachment.id)
        .where(Attachment.item_id == item_id, Attachment.original_name.like(f"%{q_lower}%"), Attachment.is_deleted.is_(False))
        .limit(1)
    ) is not None


def _hit_category(db: Session, item: Item, q_lower: str) -> bool:
    if item.category_id is None:
        return False
    return db.scalar(
        select(Category.id).where(
            Category.id == item.category_id, or_(Category.name.like(f"%{q_lower}%"), Category.slug.like(f"%{q_lower}%"))
        ).limit(1)
    ) is not None


def _hit_location(db: Session, item: Item, q_lower: str) -> bool:
    if item.location_id is None:
        return False
    return db.scalar(
        select(Location.id).where(
            Location.id == item.location_id, or_(Location.full_code.like(f"%{q_lower}%"), Location.name.like(f"%{q_lower}%"))
        ).limit(1)
    ) is not None


class SearchService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def search(
        self,
        q: str,
        limit: int = 20,
        include_archived: bool = False,
        category: str | None = None,
        location: str | None = None,
        tag: str | None = None,
    ) -> list[dict]:
        like = f"%{q}%"
        stmt = select(Item).where(fulltext_where(Item, like)).limit(limit)
        if not include_archived:
            stmt = stmt.where(Item.is_archived.is_(False))
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
                    .where(Tag.name.like(f"%{tag}%"))
                )
            )
        items = self.db.scalars(stmt).unique().all()

        location_map = self._build_map(select(Location.id, Location.full_code))
        category_map = self._build_map(select(Category.id, Category.name))
        return [self._to_result(item, q, location_map, category_map) for item in items]

    def _to_result(self, item: Item, q: str, location_map: dict, category_map: dict) -> dict:
        return {
            "id": item.id,
            "code": item.code,
            "name": item.name,
            "category_id": item.category_id,
            "category_name": category_map.get(item.category_id),
            "location_id": item.location_id,
            "location_full_code": location_map.get(item.location_id),
            "quantity": str(item.quantity) if item.quantity is not None else None,
            "unit": item.unit,
            "status": item.status,
            "cover_attachment_id": item.cover_attachment_id,
            "need_restock": item.need_restock,
            "is_favorite": item.is_favorite,
            "matched_by": compute_matched_by(self.db, item, q.lower()),
        }

    def _build_map(self, stmt) -> dict:
        return {row[0]: row[1] for row in self.db.execute(stmt).all()}
