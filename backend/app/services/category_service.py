from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError, NotFoundError
from app.models.category import Category
from app.models.item import Item
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services.validators import validate_code


DEFAULT_CATEGORIES = [
    ("元器件", "components", "ELE"),
    ("3D打印耗材", "filament", "FIL"),
    ("工具", "tools", "TOOL"),
    ("备用材料", "materials", "MAT"),
    ("线材", "cables", "CAB"),
    ("其他", "others", "OTH"),
]


class CategoryService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[Category]:
        return list(self.db.scalars(select(Category).order_by(Category.sort_order, Category.id)))

    def tree(self) -> list[dict]:
        categories = self.list()
        nodes = [
            {
                "id": category.id,
                "name": category.name,
                "slug": category.slug,
                "code_prefix": category.code_prefix,
                "parent_id": category.parent_id,
                "sort_order": category.sort_order,
                "description": category.description,
                "is_system": category.is_system,
                "created_at": category.created_at,
                "updated_at": category.updated_at,
                "children": [],
            }
            for category in categories
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

    def get(self, category_id: int) -> Category:
        category = self.db.get(Category, category_id)
        if category is None:
            raise NotFoundError("CATEGORY_NOT_FOUND", "分类不存在")
        return category

    def find_by_any(self, value: str | int | None) -> Category | None:
        if value is None:
            return None
        if isinstance(value, int) or str(value).isdigit():
            return self.db.get(Category, int(value))
        return self.db.scalar(
            select(Category).where(
                (Category.slug == str(value)) | (Category.name == str(value))
            )
        )

    def create(self, payload: CategoryCreate, is_system: bool = False) -> Category:
        validate_code(payload.code_prefix, "code_prefix")
        exists = self.db.scalar(select(Category).where(Category.slug == payload.slug))
        if exists:
            raise AppError("DUPLICATE_CODE", "分类 slug 已存在")
        category = Category(**payload.model_dump(), is_system=is_system)
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return category

    def update(self, category_id: int, payload: CategoryUpdate) -> Category:
        category = self.get(category_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(category, key, value)
        self.db.commit()
        self.db.refresh(category)
        return category

    def delete(self, category_id: int) -> None:
        category = self.get(category_id)
        has_item = self.db.scalar(select(Item.id).where(Item.category_id == category.id))
        if has_item:
            raise AppError("CATEGORY_NOT_EMPTY", "分类下还有物品，不能删除")
        self.db.delete(category)
        self.db.commit()


def init_default_categories(db: Session) -> None:
    service = CategoryService(db)
    for index, (name, slug, prefix) in enumerate(DEFAULT_CATEGORIES):
        if db.scalar(select(Category).where(Category.slug == slug)):
            continue
        service.create(
            CategoryCreate(
                name=name,
                slug=slug,
                code_prefix=prefix,
                sort_order=index * 10,
            ),
            is_system=True,
        )
