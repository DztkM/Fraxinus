from pydantic import BaseModel, ConfigDict
from datetime import datetime

class QuotaInfo(BaseModel):
    allocated: int | None
    used: int
    is_admin: bool

class AdminSetQuotaRequest(BaseModel):
    allocated_quota_bytes: int | None

class UserQuotaResponse(BaseModel):
    user_id: str
    allocated_quota_bytes: int | None
    created_at: datetime
    updated_at: datetime
    username: str | None = None

    model_config = ConfigDict(from_attributes=True)

class ClusterStorageResponse(BaseModel):
    free_bytes: int
    total_bytes: int
