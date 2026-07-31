from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import get_clerk_user, AuthContext
from core.config import settings
from models.user_quota import B2BUserQuota
from schemas.quota import UserQuotaResponse, AdminSetQuotaRequest

router = APIRouter(
    prefix="/v1/api/admin/quotas",
    tags=["admin"],
    dependencies=[Depends(get_clerk_user)]
)

async def verify_admin(auth_ctx: AuthContext = Depends(get_clerk_user)):
    if not settings.ADMIN_USER_ID or auth_ctx.user_id != settings.ADMIN_USER_ID:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return auth_ctx

@router.get("", response_model=list[UserQuotaResponse])
async def get_all_quotas(
    auth_ctx: AuthContext = Depends(verify_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(B2BUserQuota))
    return result.scalars().all()

@router.post("/{user_id}", response_model=UserQuotaResponse)
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

@router.patch("/{user_id}", response_model=UserQuotaResponse)
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
