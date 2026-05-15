from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.attachment import Attachment
from app.services.item_service import ItemService


class FileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()

    async def save_upload(
        self,
        id_or_code: str,
        file: UploadFile,
        attachment_type: str,
        is_cover: bool = False,
        description: str | None = None,
    ) -> Attachment:
        item = ItemService(self.db).get(id_or_code)
        target_dir = self.settings.upload_dir / (
            "images" if attachment_type == "image" else "attachments"
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or "").suffix.lower()
        stored_name = f"{uuid4().hex}{suffix}"
        target_path = target_dir / stored_name
        content = await file.read()
        target_path.write_bytes(content)

        attachment = Attachment(
            item_id=item.id,
            attachment_type=attachment_type,
            original_name=file.filename or stored_name,
            stored_name=stored_name,
            file_path=str(target_path.relative_to(self.settings.upload_dir.parent)),
            mime_type=file.content_type,
            size_bytes=len(content),
            description=description,
            is_cover=is_cover,
        )
        self.db.add(attachment)
        self.db.flush()
        if is_cover:
            item.cover_attachment_id = attachment.id
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

    def list_for_item(self, id_or_code: str) -> list[Attachment]:
        item = ItemService(self.db).get(id_or_code)
        return list(
            self.db.scalars(
                select(Attachment).where(
                    Attachment.item_id == item.id,
                    Attachment.is_deleted.is_(False),
                )
            )
        )

    def soft_delete(self, attachment_id: int) -> None:
        attachment = self.db.get(Attachment, attachment_id)
        if attachment:
            attachment.is_deleted = True
            self.db.commit()

    def get_download_path(self, attachment_id: int) -> tuple[Attachment, Path]:
        attachment = self.db.get(Attachment, attachment_id)
        if attachment is None or attachment.is_deleted:
            raise NotFoundError("ATTACHMENT_NOT_FOUND", "附件不存在")
        path = self.settings.upload_dir.parent / attachment.file_path
        if not path.exists():
            raise NotFoundError("ATTACHMENT_NOT_FOUND", "附件文件不存在")
        return attachment, path
