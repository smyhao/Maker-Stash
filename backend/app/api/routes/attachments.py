from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok
from app.schemas.attachment import AttachmentRead
from app.services.file_service import FileService

router = APIRouter(tags=["attachments"])


@router.post("/items/{id_or_code}/images")
async def upload_image(
    id_or_code: str,
    file: UploadFile = File(...),
    is_cover: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    attachment = await FileService(db).save_upload(id_or_code, file, "image", is_cover=is_cover)
    return ok(AttachmentRead.model_validate(attachment).model_dump())


@router.post("/items/{id_or_code}/attachments")
async def upload_attachment(
    id_or_code: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    attachment = await FileService(db).save_upload(id_or_code, file, "other")
    return ok(AttachmentRead.model_validate(attachment).model_dump())


@router.get("/items/{id_or_code}/attachments")
def list_attachments(id_or_code: str, db: Session = Depends(get_db)) -> dict:
    data = [
        AttachmentRead.model_validate(item).model_dump()
        for item in FileService(db).list_for_item(id_or_code)
    ]
    return ok({"attachments": data})


@router.delete("/attachments/{attachment_id}")
def delete_attachment(attachment_id: int, db: Session = Depends(get_db)) -> dict:
    FileService(db).soft_delete(attachment_id)
    return ok({"deleted": True})


@router.get("/attachments/{attachment_id}/download")
def download_attachment(attachment_id: int, db: Session = Depends(get_db)) -> FileResponse:
    attachment, path = FileService(db).get_download_path(attachment_id)
    return FileResponse(
        path,
        media_type=attachment.mime_type,
        filename=attachment.original_name,
    )


@router.get("/attachments/{attachment_id}/thumbnail")
def download_thumbnail(attachment_id: int, db: Session = Depends(get_db)) -> FileResponse:
    attachment, path = FileService(db).get_thumbnail_path(attachment_id)
    return FileResponse(
        path,
        media_type="image/jpeg",
        filename=f"{Path(attachment.original_name).stem}-thumb.jpg",
    )
