from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.response import ok
from app.models.backup import Backup
from app.models.category import Category
from app.models.item import Item
from app.models.location import Location

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict:
    return ok({"status": "ok"})


@router.get("/system/info")
def system_info(db: Session = Depends(get_db)) -> dict:
    settings = get_settings()
    latest_backup = db.scalar(select(Backup).order_by(Backup.created_at.desc()))
    return ok(
        {
            "name": settings.app_name,
            "version": "0.1.0",
            "environment": settings.app_env,
            "database_url": settings.database_url,
            "upload_dir": str(settings.upload_dir),
            "backup_dir": str(settings.backup_dir),
            "auth": {
                "login_enabled": settings.auth_login_enabled,
                "api_token_enabled": settings.api_token_enabled,
                "api_token_require_all": settings.api_token_require_all,
            },
            "counts": {
                "items": db.scalar(select(func.count()).select_from(Item)) or 0,
                "categories": db.scalar(select(func.count()).select_from(Category)) or 0,
                "locations": db.scalar(select(func.count()).select_from(Location)) or 0,
            },
            "latest_backup": latest_backup.backup_id if latest_backup else None,
        }
    )
