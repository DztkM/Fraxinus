import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.config import settings
from models.namespace import Namespace
from schemas.b2b import B2BTokenRequest, B2BTokenResponse

router = APIRouter(
    prefix="/v1/api/b2b",
    tags=["b2b"]
)

@router.post("/auth/token", response_model=B2BTokenResponse)
async def login_for_access_token(
    request: B2BTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    key_hash = hashlib.sha256(request.api_key.encode()).hexdigest()
    
    result = await db.execute(select(Namespace).where(Namespace.api_key_hash == key_hash))
    namespace = result.scalars().first()
    
    if not namespace:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
        
    # Generate JWT
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    
    payload = {
        "namespace_id": str(namespace.id),
        "exp": expire,
        "iss": "fraxinus-b2b"
    }
    
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    
    return B2BTokenResponse(access_token=token)
