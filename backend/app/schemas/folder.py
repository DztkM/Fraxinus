import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from schemas.file import FileResponse

class FolderCreateRequest(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None

class FolderUpdateRequest(BaseModel):
    name: str

class FolderAccessUpdateRequest(BaseModel):
    set_access_level: int
    allowed_users: list[str] | None = None

class FolderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    path: str | None
    set_access_level: int
    actual_access_level: int
    created_at: datetime

class FolderContentsResponse(BaseModel):
    folders: list[FolderResponse]
    files: list[FileResponse]
