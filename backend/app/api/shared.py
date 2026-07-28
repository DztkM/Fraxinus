from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user, AuthContext
from models.folder import Folder
from models.file import File
from models.permissions import FolderAllowedUser, FileAllowedUser
from schemas.shared import SharedListResponse

router = APIRouter(prefix="/api/shared", tags=["shared"])

@router.get("/", response_model=SharedListResponse)
async def get_shared_items(
    auth_ctx: AuthContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get explicitly shared folders
    shared_folders = await db.execute(
        select(Folder)
        .join(FolderAllowedUser)
        .where(
            FolderAllowedUser.user_id == auth_ctx.user_id,
            Folder.namespace_id == auth_ctx.namespace_id
        )
    )
    folders = shared_folders.scalars().all()
    
    # Get explicitly shared files
    shared_files = await db.execute(
        select(File)
        .join(FileAllowedUser)
        .where(
            FileAllowedUser.user_id == auth_ctx.user_id,
            File.namespace_id == auth_ctx.namespace_id
        )
    )
    files = shared_files.scalars().all()
    
    items = []
    for f in folders:
        items.append({
            "id": f.id,
            "name": f.name,
            "author_id": f.author_id,
            "status": None,
            "created_at": f.created_at,
            "type": "folder"
        })
    for f in files:
        items.append({
            "id": f.id,
            "name": f.original_name,
            "author_id": f.uploader_id,
            "status": f.status,
            "created_at": f.created_at,
            "type": "file"
        })
        
    return {"items": items}
