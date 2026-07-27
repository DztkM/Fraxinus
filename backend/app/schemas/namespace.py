from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime

class NamespaceBase(BaseModel):
    name: str
    storage_quota_bytes: int | None = None

class NamespaceCreate(NamespaceBase):
    pass

class NamespaceResponse(NamespaceBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class NamespaceCreateResponse(NamespaceResponse):
    api_key: str
