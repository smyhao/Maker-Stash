from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
def search(q: str, limit: int = 20, include_archived: bool = False, db: Session = Depends(get_db)) -> dict:
    return ok({"items": SearchService(db).search(q, limit, include_archived)})
