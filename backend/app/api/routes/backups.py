from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.backup import BackupCreate, BackupRead
from app.services.backup_service import BackupService

router = APIRouter(prefix="/backups", tags=["backups"])


@router.post("")
def create_backup(payload: BackupCreate, db: Session = Depends(get_db)) -> dict:
    backup = BackupService(db).create(payload.include_uploads, payload.note)
    return ok(BackupRead.model_validate(backup).model_dump())


@router.get("")
def list_backups(db: Session = Depends(get_db)) -> dict:
    data = [BackupRead.model_validate(item).model_dump() for item in BackupService(db).list()]
    return ok({"backups": data})


@router.post("/{backup_id}/restore")
def restore_backup(backup_id: str, db: Session = Depends(get_db)) -> dict:
    backup = BackupService(db).restore(backup_id)
    return ok(BackupRead.model_validate(backup).model_dump())


@router.get("/{backup_id}/download")
def download_backup(backup_id: str, db: Session = Depends(get_db)) -> FileResponse:
    backup, path = BackupService(db).get_download_path(backup_id)
    return FileResponse(path, media_type="application/zip", filename=f"{backup.backup_id}.zip")
