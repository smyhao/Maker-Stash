from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AttachmentRead(BaseModel):
    id: int
    item_id: int
    attachment_type: str
    original_name: str
    stored_name: str
    file_path: str
    mime_type: str | None
    size_bytes: int | None
    description: str | None
    is_cover: bool
    is_deleted: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
