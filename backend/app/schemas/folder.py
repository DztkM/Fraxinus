import uuid
from datetime import datetime
from pydantic import BaseModel

from schemas.file import FileResponse

class FolderCreateRequest(BaseModel):
    name: str
    parent_id: uuid.UUID | None = None

class FolderUpdateRequest(BaseModel):
    name: str

class FolderResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    path: str | None
    created_at: datetime

    class Config:
        from_attributes = True

class FolderContentsResponse(BaseModel):
    folders: list[FolderResponse]
    files: list[FileResponse]
