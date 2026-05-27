from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.common import WriteMetadata


class TaskCreate(WriteMetadata):
    job_type: str
    input_summary: str | None = None


class TaskRead(BaseModel):
    task_id: str
    status: str
    job_type: str
    input_summary: str | None
    result_summary: str | None
    error_message: str | None
    source: str
    module: str | None
    operator: str | None
    request_id: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TaskStatusRead(BaseModel):
    task_id: str
    status: str
    job_type: str
    error: dict[str, str] | None = None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)
