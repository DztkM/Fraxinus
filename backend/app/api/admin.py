from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from core.database import get_db
from core.auth import get_clerk_user, AuthContext
from core.config import settings
from models.user_quota import B2BUserQuota
from schemas.quota import UserQuotaResponse, AdminSetQuotaRequest

router = APIRouter(
    prefix="/v1/api/admin",
    tags=["admin"],
    dependencies=[Depends(get_clerk_user)]
)

async def verify_admin(auth_ctx: AuthContext = Depends(get_clerk_user)):
    if not auth_ctx.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return auth_ctx

@router.get("/quotas", response_model=list[UserQuotaResponse])
async def get_all_quotas(
    auth_ctx: AuthContext = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(B2BUserQuota))
    quotas = result.scalars().all()
    
    username_map = {}
    if quotas and settings.CLERK_SECRET_KEY:
        user_ids = [q.user_id for q in quotas]
        async with httpx.AsyncClient() as client:
            for i in range(0, len(user_ids), 50):
                chunk = user_ids[i:i+50]
                params = [("user_id", uid) for uid in chunk]
                try:
                    response = await client.get(
                        "https://api.clerk.com/v1/users",
                        headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
                        params=params
                    )
                    if response.status_code == 200:
                        for u in response.json():
                            username = u.get("username")
                            if not username:
                                primary_id = u.get("primary_email_address_id")
                                for e in u.get("email_addresses", []):
                                    if e.get("id") == primary_id:
                                        username = e.get("email_address")
                                        break
                            username_map[u["id"]] = username
                except Exception:
                    pass
                    
    return [
        UserQuotaResponse(
            user_id=q.user_id,
            allocated_quota_bytes=q.allocated_quota_bytes,
            created_at=q.created_at,
            updated_at=q.updated_at,
            username=username_map.get(q.user_id)
        ) for q in quotas
    ]

@router.post("/quotas/{user_id}", response_model=UserQuotaResponse)
async def set_user_quota(
    user_id: str,
    request: AdminSetQuotaRequest,
    auth_ctx: AuthContext = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(B2BUserQuota).where(B2BUserQuota.user_id == user_id))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Quota for this user already exists. Use PATCH to update."
        )

    quota = B2BUserQuota(
        user_id=user_id,
        allocated_quota_bytes=request.allocated_quota_bytes
    )
    db.add(quota)

    await db.commit()
    await db.refresh(quota)
    return quota

@router.patch("/quotas/{user_id}", response_model=UserQuotaResponse)
async def change_user_quota(
    user_id: str,
    request: AdminSetQuotaRequest,
    auth_ctx: AuthContext = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(B2BUserQuota).where(B2BUserQuota.user_id == user_id))
    quota = result.scalar_one_or_none()

    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quota for this user not found. Use POST to create."
        )

    quota.allocated_quota_bytes = request.allocated_quota_bytes

    await db.commit()
    await db.refresh(quota)
    return quota

@router.get("/users")
async def search_users(
    query: str = "",
    auth_ctx: AuthContext = Depends(verify_admin)
):
    if not settings.CLERK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="CLERK_SECRET_KEY is not configured")
    
    async with httpx.AsyncClient() as client:
        params = {"query": query, "limit": 10} if query else {"limit": 10}
        response = await client.get(
            "https://api.clerk.com/v1/users",
            headers={"Authorization": f"Bearer {settings.CLERK_SECRET_KEY}"},
            params=params
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch users from Clerk")
        
        users_data = response.json()
        
        result = []
        for u in users_data:
            username = u.get("username")
            
            # If a query is provided, enforce that it matches the username partially
            if query and username:
                if query.lower() not in username.lower():
                    continue
            elif query and not username:
                # If there's a query but user has no username, it's not a match by username
                continue
                
            email = "Unknown"
            primary_id = u.get("primary_email_address_id")
            for e in u.get("email_addresses", []):
                if e.get("id") == primary_id:
                    email = e.get("email_address")
                    break
            if email == "Unknown" and u.get("email_addresses"):
                email = u["email_addresses"][0].get("email_address")
            
            result.append({
                "id": u.get("id"),
                "username": username or "",
                "email": email,
                "first_name": u.get("first_name") or "",
                "last_name": u.get("last_name") or ""
            })
            
        return result

