from pydantic import BaseModel


class WriteMetadata(BaseModel):
    source: str = "api"
    module: str | None = None
    operator: str | None = None
    request_id: str | None = None
