from pydantic import BaseModel, ConfigDict, Field, computed_field
import uuid
from datetime import datetime

class NamespaceBase(BaseModel):
    name: str
    quota_bytes: int | None = None

class NamespaceCreate(NamespaceBase):
    pass

class ApiKeyInfo(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ApiKeyCreate(BaseModel):
    name: str
    namespace_id: uuid.UUID

class NamespaceResponse(NamespaceBase):
    id: uuid.UUID
    used_bytes: int
    files_count: int
    created_at: datetime
    updated_at: datetime
    
    api_keys: list[ApiKeyInfo] = Field(default_factory=list)
    
    model_config = ConfigDict(from_attributes=True)

class NamespaceCreateResponse(NamespaceResponse):
    pass

class ApiKeyResponse(ApiKeyInfo):
    api_key: str
