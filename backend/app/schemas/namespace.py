from pydantic import BaseModel, ConfigDict, Field, computed_field
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
    
    api_key_hash: str | None = Field(default=None, exclude=True)
    
    @computed_field
    @property
    def has_api_key(self) -> bool:
        return self.api_key_hash is not None
    
    model_config = ConfigDict(from_attributes=True)

class NamespaceCreateResponse(NamespaceResponse):
    api_key: str

class ApiKeyResponse(BaseModel):
    api_key: str
