import uuid
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import async_session_maker
from models.folder import Folder
from models.file import File

logger = logging.getLogger(__name__)

async def recalculate_folder_access(folder_id: uuid.UUID, session: AsyncSession = None):
    """
    Recalculate actual_access_level for all descendants of a folder using BFS.
    """
    try:
        if session:
            await _recalculate(folder_id, session)
        else:
            async with async_session_maker() as new_session:
                await _recalculate(folder_id, new_session)
    except Exception as e:
        logger.error(f"Error recalculating folder access for {folder_id}: {e}")

async def _recalculate(folder_id: uuid.UUID, session: AsyncSession):
    result = await session.execute(select(Folder).where(Folder.id == folder_id))
    folder = result.scalar_one_or_none()
    if not folder:
        return
    
    queue = [(folder.id, folder.actual_access_level)]
            
    while queue:
        current_id, current_actual_access_level = queue.pop(0)
        
        # Fetch children folders
        children_result = await session.execute(
            select(Folder).where(Folder.parent_id == current_id)
        )
        children = children_result.scalars().all()
        
        for child in children:
            new_actual = max(child.set_access_level, current_actual_access_level)
            if child.actual_access_level != new_actual:
                child.actual_access_level = new_actual
            queue.append((child.id, new_actual))
            
        # Fetch children files
        files_result = await session.execute(
            select(File).where(File.folder_id == current_id)
        )
        files = files_result.scalars().all()
        
        for f in files:
            new_actual = max(f.set_access_level, current_actual_access_level)
            if f.actual_access_level != new_actual:
                f.actual_access_level = new_actual
        
    await session.commit()
