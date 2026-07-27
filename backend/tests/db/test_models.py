import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from models.folder import Folder
from models.physical_file import PhysicalFile
from models.file import File
from models.permissions import FolderAllowedUser, FileAllowedUser
from models.share_link import ShareLink
from core.auth import CLERK_NAMESPACE_ID

@pytest.mark.asyncio
async def test_create_folder(db_session):
    """
    Test creating a folder and saving it to the database.
    """
    new_folder = Folder(
        name="test_folder",
        author_id="user123",
        namespace_id=CLERK_NAMESPACE_ID
        # path could be set if ltree is manually managed, e.g. "root.test_folder"
    )
    db_session.add(new_folder)
    await db_session.commit()
    
    # Verify it was created
    result = await db_session.execute(select(Folder).filter_by(name="test_folder"))
    folder = result.scalar_one_or_none()
    
    assert folder is not None
    assert folder.author_id == "user123"
    assert folder.set_access_level == 1  # Default value
    assert folder.actual_access_level == 1  # Default value

@pytest.mark.asyncio
async def test_create_folder_hierarchy(db_session):
    """
    Test creating a folder inside another folder (parent_id relationship).
    """
    parent_folder = Folder(name="parent", author_id="user1", namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(parent_folder)
    await db_session.commit()
    await db_session.refresh(parent_folder)
    
    child_folder = Folder(name="child", parent_id=parent_folder.id, author_id="user1", namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(child_folder)
    await db_session.commit()
    
    # Verify the child has the correct parent
    result = await db_session.execute(select(Folder).filter_by(name="child"))
    child = result.scalar_one_or_none()
    
    assert child is not None
    assert child.parent_id == parent_folder.id

@pytest.mark.asyncio
async def test_create_physical_and_logical_file(db_session):
    """
    Test the relation between PhysicalFile and File.
    """
    phys_file = PhysicalFile(
        internal_key="minio_key_123",
        file_hash="abcd1234hash",
        size=1024,
        mime_type="text/plain"
    )
    db_session.add(phys_file)
    await db_session.commit()
    await db_session.refresh(phys_file)
    
    logical_file = File(
        original_name="document.txt",
        uploader_id="user456",
        status="completed",
        namespace_id=CLERK_NAMESPACE_ID,
        physical_file_id=phys_file.id
    )
    db_session.add(logical_file)
    await db_session.commit()
    
    # Verify logical file is attached to physical file
    result = await db_session.execute(select(File).filter_by(original_name="document.txt"))
    file_record = result.scalar_one_or_none()
    
    assert file_record is not None
    assert file_record.physical_file_id == phys_file.id
    assert file_record.status == "completed"

@pytest.mark.asyncio
async def test_folder_delete_restrict_children(db_session):
    """
    Test that deleting a folder with child folders fails due to RESTRICT.
    """
    parent_folder = Folder(name="parent", author_id="user1", namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(parent_folder)
    await db_session.flush()
    
    child_folder = Folder(name="child", parent_id=parent_folder.id, author_id="user1", namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(child_folder)
    await db_session.commit()
    
    # Attempt to delete parent
    await db_session.delete(parent_folder)
    with pytest.raises(IntegrityError):
        await db_session.commit()
        
@pytest.mark.asyncio
async def test_folder_delete_restrict_files(db_session):
    """
    Test that deleting a folder with files fails due to RESTRICT.
    """
    folder = Folder(name="folder_with_files", author_id="user1", namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(folder)
    await db_session.flush()
    
    phys_file = PhysicalFile(internal_key="key", file_hash="hash", size=1, mime_type="text")
    db_session.add(phys_file)
    await db_session.flush()
    
    file = File(original_name="test.txt", uploader_id="user1", physical_file_id=phys_file.id, folder_id=folder.id, namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(file)
    await db_session.commit()
    
    await db_session.delete(folder)
    with pytest.raises(IntegrityError):
        await db_session.commit()

@pytest.mark.asyncio
async def test_folder_delete_cascade_permissions(db_session):
    """
    Test that deleting a folder cascades to its permissions and share links.
    """
    folder = Folder(name="empty_folder", author_id="user1", namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(folder)
    await db_session.flush()
    
    perm = FolderAllowedUser(folder_id=folder.id, user_id="user2")
    db_session.add(perm)
    
    import uuid
    from datetime import datetime, timezone, timedelta
    
    link = ShareLink(
        token="folder_token", 
        folder_id=folder.id, 
        created_by=uuid.uuid4(), 
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(link)
    await db_session.commit()
    
    # Delete folder
    await db_session.delete(folder)
    await db_session.commit()
    
    # Verify permissions and links are deleted
    perms = await db_session.execute(select(FolderAllowedUser).filter_by(folder_id=folder.id))
    assert perms.scalar_one_or_none() is None
    
    links = await db_session.execute(select(ShareLink).filter_by(folder_id=folder.id))
    assert links.scalar_one_or_none() is None

@pytest.mark.asyncio
async def test_file_delete_cascade_permissions(db_session):
    """
    Test that deleting a file cascades to its permissions and share links.
    """
    phys_file = PhysicalFile(internal_key="key2", file_hash="hash2", size=1, mime_type="text")
    db_session.add(phys_file)
    await db_session.flush()
    
    file = File(original_name="file_to_delete.txt", uploader_id="user1", physical_file_id=phys_file.id, namespace_id=CLERK_NAMESPACE_ID)
    db_session.add(file)
    await db_session.flush()
    
    perm = FileAllowedUser(file_id=file.id, user_id="user2")
    db_session.add(perm)
    
    import uuid
    from datetime import datetime, timezone, timedelta
    
    link = ShareLink(
        token="file_token", 
        file_id=file.id, 
        created_by=uuid.uuid4(), 
        expires_at=datetime.now(timezone.utc) + timedelta(days=1)
    )
    db_session.add(link)
    await db_session.commit()
    
    # Delete file
    await db_session.delete(file)
    await db_session.commit()
    
    perms = await db_session.execute(select(FileAllowedUser).filter_by(file_id=file.id))
    assert perms.scalar_one_or_none() is None
    
    links = await db_session.execute(select(ShareLink).filter_by(file_id=file.id))
    assert links.scalar_one_or_none() is None

