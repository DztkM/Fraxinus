import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class FileUploadInitRequest(BaseModel):
    original_name: str
    size: int
    mime_type: str
    parts_count: int
    folder_id: uuid.UUID | None = None

class FileUpdateRequest(BaseModel):
    original_name: str

class FileAccessUpdateRequest(BaseModel):
    set_access_level: int
    allowed_users: list[str] | None = None

class FileUploadInitResponse(BaseModel):
    file_id: uuid.UUID
    upload_id: str
    presigned_urls: dict[int, str]

class FileUploadPart(BaseModel):
    PartNumber: int
    ETag: str

class FileUploadCompleteRequest(BaseModel):
    upload_id: str
    parts: list[FileUploadPart]

class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    original_name: str
    status: str
    set_access_level: int
    actual_access_level: int
    author_id: str
    created_at: datetime

class FileDownloadResponse(BaseModel):
    url: str
    original_name: str
