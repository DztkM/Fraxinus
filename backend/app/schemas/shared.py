import uuid
from datetime import datetime
from pydantic import BaseModel

class SharedItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    author_id: str
    status: str | None = None
    created_at: datetime
    type: str

class SharedListResponse(BaseModel):
    items: list[SharedItemResponse]
