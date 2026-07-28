import secrets
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import get_clerk_user, AuthContext
from models.namespace import Namespace
from schemas.namespace import NamespaceCreate, NamespaceResponse, NamespaceCreateResponse, ApiKeyResponse
import uuid

router = APIRouter(
    prefix="/v1/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_clerk_user)]
)

def generate_api_key() -> tuple[str, str]:
    """Generates a raw API key and its SHA-256 hash."""
    # Prefix helps identify the key later if needed
    raw_key = "frax_" + secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash

@router.post("/namespaces", response_model=NamespaceCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_namespace(
    namespace_in: NamespaceCreate,
    auth_ctx: AuthContext = Depends(get_clerk_user),
    db: AsyncSession = Depends(get_db)
):
    # Check if namespace with this name already exists
    result = await db.execute(select(Namespace).where(Namespace.name == namespace_in.name))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Namespace with this name already exists"
        )
    
    raw_key, key_hash = generate_api_key()
    
    new_namespace = Namespace(
        name=namespace_in.name,
        storage_quota_bytes=namespace_in.storage_quota_bytes,
        api_key_hash=key_hash,
        author_id=auth_ctx.user_id
    )
    
    db.add(new_namespace)
    await db.commit()
    await db.refresh(new_namespace)
    
    # Return response including the raw API key (this is the only time it's shown)
    return NamespaceCreateResponse(
        id=new_namespace.id,
        name=new_namespace.name,
        storage_quota_bytes=new_namespace.storage_quota_bytes,
        created_at=new_namespace.created_at,
        updated_at=new_namespace.updated_at,
        api_key=raw_key
    )

@router.get("/namespaces", response_model=list[NamespaceResponse])
async def get_namespaces(
    auth_ctx: AuthContext = Depends(get_clerk_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Namespace).where(Namespace.author_id == auth_ctx.user_id))
    namespaces = result.scalars().all()
    return namespaces

@router.post("/namespaces/{namespace_id}/api-key", response_model=ApiKeyResponse)
async def generate_new_api_key(
    namespace_id: uuid.UUID,
    auth_ctx: AuthContext = Depends(get_clerk_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Namespace).where(
            Namespace.id == namespace_id, 
            Namespace.author_id == auth_ctx.user_id
        )
    )
    namespace = result.scalar_one_or_none()
    
    if not namespace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Namespace not found")
        
    raw_key, key_hash = generate_api_key()
    
    namespace.api_key_hash = key_hash
    await db.commit()
    
    return ApiKeyResponse(api_key=raw_key)

@router.delete("/namespaces/{namespace_id}/api-key", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    namespace_id: uuid.UUID,
    auth_ctx: AuthContext = Depends(get_clerk_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Namespace).where(
            Namespace.id == namespace_id, 
            Namespace.author_id == auth_ctx.user_id
        )
    )
    namespace = result.scalar_one_or_none()
    
    if not namespace:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Namespace not found")
        
    namespace.api_key_hash = None
    await db.commit()
    
    return None
