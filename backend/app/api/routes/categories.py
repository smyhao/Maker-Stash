from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.category import CategoryCreate, CategoryRead, CategoryTreeNode, CategoryUpdate
from app.services.category_service import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def list_categories(db: Session = Depends(get_db)) -> dict:
    data = [CategoryRead.model_validate(item).model_dump() for item in CategoryService(db).list()]
    return ok({"categories": data})


@router.get("/tree")
def category_tree(db: Session = Depends(get_db)) -> dict:
    data = [CategoryTreeNode.model_validate(item).model_dump() for item in CategoryService(db).tree()]
    return ok({"categories": data})


@router.post("")
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)) -> dict:
    category = CategoryService(db).create(payload)
    return ok(CategoryRead.model_validate(category).model_dump())


@router.patch("/{category_id}")
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)) -> dict:
    category = CategoryService(db).update(category_id, payload)
    return ok(CategoryRead.model_validate(category).model_dump())


@router.delete("/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)) -> dict:
    CategoryService(db).delete(category_id)
    return ok({"deleted": True})
