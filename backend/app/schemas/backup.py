from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BackupCreate(BaseModel):
    include_uploads: bool = True
    note: str | None = None


class BackupRead(BaseModel):
    id: int
    backup_id: str
    file_path: str
    size_bytes: int | None
    include_uploads: bool
    note: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
