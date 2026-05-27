from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile, status
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, NotFoundError
from app.models.attachment import Attachment
from app.models.item import Item
from app.services.file_storage import delete_upload_relative_file
from app.services.item_service import ItemService


class FileService:
    CHUNK_SIZE = 1024 * 1024
    THUMBNAIL_SIZE = (320, 240)
    ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

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
        self._validate_upload(file, attachment_type)
        target_dir = self.settings.upload_dir / (
            "images" if attachment_type == "image" else "attachments"
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename or "").suffix.lower()
        stored_name = f"{uuid4().hex}{suffix}"
        target_path = target_dir / stored_name
        size_bytes = 0
        try:
            with target_path.open("wb") as output:
                while chunk := await file.read(self.CHUNK_SIZE):
                    size_bytes += len(chunk)
                    if size_bytes > self.settings.max_upload_bytes:
                        output.close()
                        target_path.unlink(missing_ok=True)
                        raise AppError("UPLOAD_TOO_LARGE", "上传文件超过大小限制", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
                    output.write(chunk)
        finally:
            await file.close()

        thumbnail_path: str | None = None
        if attachment_type == "image":
            try:
                thumbnail_path = self._create_thumbnail(target_path)
            except UnidentifiedImageError:
                target_path.unlink(missing_ok=True)
                raise AppError("UPLOAD_FAILED", "图片文件无法解析", status.HTTP_400_BAD_REQUEST) from None

        attachment = Attachment(
            item_id=item.id,
            attachment_type=attachment_type,
            original_name=file.filename or stored_name,
            stored_name=stored_name,
            file_path=target_path.relative_to(self.settings.upload_dir.parent).as_posix(),
            thumbnail_path=thumbnail_path,
            mime_type=file.content_type,
            size_bytes=size_bytes,
            description=description,
            is_cover=is_cover,
        )
        self.db.add(attachment)
        self.db.flush()
        if is_cover:
            self._clear_existing_cover_flags(item.id)
            attachment.is_cover = True
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
            delete_upload_relative_file(attachment.file_path)
            delete_upload_relative_file(attachment.thumbnail_path)
            attachment.is_deleted = True
            attachment.is_cover = False
            item = self.db.get(Item, attachment.item_id)
            if item and item.cover_attachment_id == attachment.id:
                item.cover_attachment_id = None
            self.db.commit()

    def _clear_existing_cover_flags(self, item_id: int) -> None:
        self.db.execute(
            update(Attachment)
            .where(Attachment.item_id == item_id, Attachment.is_cover.is_(True))
            .values(is_cover=False)
        )

    def get_download_path(self, attachment_id: int) -> tuple[Attachment, Path]:
        attachment = self.db.get(Attachment, attachment_id)
        if attachment is None or attachment.is_deleted:
            raise NotFoundError("ATTACHMENT_NOT_FOUND", "附件不存在")
        path = self.settings.upload_dir.parent / attachment.file_path
        if not path.exists():
            raise NotFoundError("ATTACHMENT_NOT_FOUND", "附件文件不存在")
        return attachment, path

    def get_thumbnail_path(self, attachment_id: int) -> tuple[Attachment, Path]:
        attachment = self.db.get(Attachment, attachment_id)
        if attachment is None or attachment.is_deleted or not attachment.thumbnail_path:
            raise NotFoundError("THUMBNAIL_NOT_FOUND", "缩略图不存在")
        path = self.settings.upload_dir.parent / attachment.thumbnail_path
        if not path.exists():
            raise NotFoundError("THUMBNAIL_NOT_FOUND", "缩略图文件不存在")
        return attachment, path

    def _validate_upload(self, file: UploadFile, attachment_type: str) -> None:
        if attachment_type == "image" and file.content_type not in self.ALLOWED_IMAGE_MIME_TYPES:
            raise AppError("UPLOAD_FAILED", "图片只支持 JPEG、PNG、WebP 或 GIF")

    def _create_thumbnail(self, source_path: Path) -> str:
        thumbnail_dir = self.settings.upload_dir / "thumbnails"
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        thumbnail_path = thumbnail_dir / f"{source_path.stem}.jpg"

        with Image.open(source_path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail(self.THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
            if image.mode in {"RGBA", "LA", "P"}:
                image = image.convert("RGBA")
                background = Image.new("RGBA", image.size, (255, 255, 255, 255))
                background.alpha_composite(image)
                image = background.convert("RGB")
            else:
                image = image.convert("RGB")
            image.save(thumbnail_path, format="JPEG", quality=82, optimize=True)

        return thumbnail_path.relative_to(self.settings.upload_dir.parent).as_posix()
