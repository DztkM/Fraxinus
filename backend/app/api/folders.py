import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.auth import get_current_user
from models.folder import Folder
from models.file import File
from schemas.folder import FolderCreateRequest, FolderResponse, FolderContentsResponse, FolderUpdateRequest

router = APIRouter(prefix="/api/folders", tags=["folders"])

def format_ltree(uuid_val: uuid.UUID | str) -> str:
    return str(uuid_val).replace("-", "_")

@router.post("/", response_model=FolderResponse)
async def create_folder(
    request: FolderCreateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    folder_id = uuid.uuid4()
    path = format_ltree(folder_id)
    
    if request.parent_id:
        parent_result = await db.execute(select(Folder).where(Folder.id == request.parent_id))
        parent_folder = parent_result.scalar_one_or_none()
        if not parent_folder:
            raise HTTPException(status_code=404, detail="Parent folder not found")
        if parent_folder.author_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied") #TODO change to 404 in prod
            
        if parent_folder.path:
            path = f"{parent_folder.path}.{path}"

    new_folder = Folder(
        id=folder_id,
        name=request.name,
        parent_id=request.parent_id,
        path=path,
        author_id=user_id,
    )
    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)
    
    return new_folder

@router.get("/root/contents", response_model=FolderContentsResponse)
async def get_root_contents(
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    folders_result = await db.execute(
        select(Folder).where(Folder.author_id == user_id, Folder.parent_id == None)
    )
    folders = folders_result.scalars().all()
    
    files_result = await db.execute(
        select(File).where(File.uploader_id == user_id, File.folder_id == None)
    )
    files = files_result.scalars().all()
    
    return FolderContentsResponse(folders=folders, files=files)

@router.get("/{folder_id}/contents", response_model=FolderContentsResponse)
async def get_folder_contents(
    folder_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify folder exists and belongs to user
    folder_result = await db.execute(select(Folder).where(Folder.id == folder_id))
    folder = folder_result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    if folder.author_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied") #TODO change to 404 in prod
        
    folders_result = await db.execute(
        select(Folder).where(Folder.author_id == user_id, Folder.parent_id == folder_id)
    )
    folders = folders_result.scalars().all()
    
    files_result = await db.execute(
        select(File).where(File.uploader_id == user_id, File.folder_id == folder_id)
    )
    files = files_result.scalars().all()
    
    return FolderContentsResponse(folders=folders, files=files)

@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    if folder.author_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied") #TODO change to 404 in prod
        
    # Check for child folders
    child_folders_result = await db.execute(
        select(Folder).where(Folder.parent_id == folder_id).limit(1)
    )
    if child_folders_result.scalars().first():
        raise HTTPException(status_code=400, detail="Folder is not empty (contains folders)")
        
    # Check for child files
    child_files_result = await db.execute(
        select(File).where(File.folder_id == folder_id).limit(1)
    )
    if child_files_result.scalars().first():
        raise HTTPException(status_code=400, detail="Folder is not empty (contains files)")
        
    await db.delete(folder)
    await db.commit()
    return None

@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: uuid.UUID,
    request: FolderUpdateRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    if folder.author_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied") #TODO change to 404 in prod
        
    folder.name = request.name
    await db.commit()
    await db.refresh(folder)
    return folder
