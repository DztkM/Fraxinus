import pytest
import asyncio
import uuid
from core.tasks import recalculate_folder_access

@pytest.mark.asyncio
async def test_update_folder_access(client):
    # 1. Create folder
    folder_resp = await client.post("/v1/api/folders/", json={"name": "Access Folder"})
    assert folder_resp.status_code == 200
    folder_id = folder_resp.json()["id"]
    
    # 2. Update access to level 2
    patch_data = {
        "set_access_level": 2,
        "allowed_users": ["user2", "user3"]
    }
    patch_resp = await client.patch(f"/v1/api/folders/{folder_id}/access", json=patch_data)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["set_access_level"] == 2
    assert patch_resp.json()["actual_access_level"] == 2

@pytest.mark.asyncio
async def test_folder_access_invalid_level(client):
    folder_resp = await client.post("/v1/api/folders/", json={"name": "Access Folder 2"})
    folder_id = folder_resp.json()["id"]
    
    # Update to invalid level
    patch_data = {
        "set_access_level": 5,
    }
    patch_resp = await client.patch(f"/v1/api/folders/{folder_id}/access", json=patch_data)
    assert patch_resp.status_code == 400
    assert "Invalid access level" in patch_resp.json()["detail"]

@pytest.mark.asyncio
async def test_file_access_propagation(client, mock_s3, db_session):
    # 1. Create parent folder
    parent_resp = await client.post("/v1/api/folders/", json={"name": "Parent Folder"})
    parent_id = parent_resp.json()["id"]
    
    # 2. Init upload of a file to this folder
    init_data = {
        "original_name": "child_file.txt",
        "size": 100,
        "mime_type": "text/plain",
        "parts_count": 1,
        "folder_id": parent_id
    }
    init_resp = await client.post("/v1/api/files/upload/init", json=init_data)
    file_id = init_resp.json()["file_id"]
    
    # 3. Update parent folder access to 3
    patch_resp = await client.patch(f"/v1/api/folders/{parent_id}/access", json={"set_access_level": 3})
    assert patch_resp.status_code == 200
    
    # Manually run the background task logic with test db_session to see uncommitted data
    await recalculate_folder_access(uuid.UUID(parent_id), db_session)
    
    # 4. Check file access level
    list_resp = await client.get("/v1/api/files/")
    files = list_resp.json()
    file_record = next(f for f in files if f["id"] == file_id)
    assert file_record["actual_access_level"] == 3

@pytest.mark.asyncio
async def test_shared_endpoint(client):
    # 1. Create folder
    folder_resp = await client.post("/v1/api/folders/", json={"name": "Shared Folder"})
    folder_id = folder_resp.json()["id"]
    
    # 2. Share it
    patch_data = {
        "set_access_level": 2,
        "allowed_users": ["test_user_123"]
    }
    await client.patch(f"/v1/api/folders/{folder_id}/access", json=patch_data)
    
    # 3. Get shared items
    shared_resp = await client.get("/v1/api/shared/")
    assert shared_resp.status_code == 200
    shared_items = shared_resp.json()["items"]
    
    assert any(item["id"] == folder_id for item in shared_items)

@pytest.mark.asyncio
async def test_file_access_propagation_deep_higher(client, mock_s3, db_session):
    root_resp = await client.post("/v1/api/folders/", json={"name": "Root"})
    root_id = root_resp.json()["id"]

    sub1_resp = await client.post("/v1/api/folders/", json={"name": "Sub 1", "parent_id": root_id})
    sub1_id = sub1_resp.json()["id"]

    sub2_resp = await client.post("/v1/api/folders/", json={"name": "Sub 2", "parent_id": root_id})
    sub2_id = sub2_resp.json()["id"]
    await client.patch(f"/v1/api/folders/{sub2_id}/access", json={"set_access_level": 3})
    await recalculate_folder_access(uuid.UUID(sub2_id), db_session)

    f1_resp = await client.post("/v1/api/files/upload/init", json={"original_name": "f1.txt", "size": 1, "mime_type": "text/plain", "parts_count": 1, "folder_id": sub1_id})
    f1_id = f1_resp.json()["file_id"]

    f2_resp = await client.post("/v1/api/files/upload/init", json={"original_name": "f2.txt", "size": 1, "mime_type": "text/plain", "parts_count": 1, "folder_id": sub2_id})
    f2_id = f2_resp.json()["file_id"]

    await client.patch(f"/v1/api/folders/{root_id}/access", json={"set_access_level": 2, "allowed_users": ["u1"]})
    await recalculate_folder_access(uuid.UUID(root_id), db_session)

    sub1 = await client.get(f"/v1/api/folders/{root_id}/contents")
    s1 = next(f for f in sub1.json()["folders"] if f["id"] == sub1_id)
    assert s1["actual_access_level"] == 2

    s2 = next(f for f in sub1.json()["folders"] if f["id"] == sub2_id)
    assert s2["actual_access_level"] == 3

    f1_contents = await client.get(f"/v1/api/folders/{sub1_id}/contents")
    file1 = next(f for f in f1_contents.json()["files"] if f["id"] == f1_id)
    assert file1["actual_access_level"] == 2

    f2_contents = await client.get(f"/v1/api/folders/{sub2_id}/contents")
    file2 = next(f for f in f2_contents.json()["files"] if f["id"] == f2_id)
    assert file2["actual_access_level"] == 3

@pytest.mark.asyncio
async def test_file_access_propagation_deep_lower(client, mock_s3, db_session):
    root_resp = await client.post("/v1/api/folders/", json={"name": "Root"})
    root_id = root_resp.json()["id"]
    await client.patch(f"/v1/api/folders/{root_id}/access", json={"set_access_level": 3})
    await recalculate_folder_access(uuid.UUID(root_id), db_session)

    sub1_resp = await client.post("/v1/api/folders/", json={"name": "Sub 1", "parent_id": root_id})
    sub1_id = sub1_resp.json()["id"]
    await client.patch(f"/v1/api/folders/{sub1_id}/access", json={"set_access_level": 2, "allowed_users": ["u1"]})
    await recalculate_folder_access(uuid.UUID(sub1_id), db_session)

    sub2_resp = await client.post("/v1/api/folders/", json={"name": "Sub 2", "parent_id": root_id})
    sub2_id = sub2_resp.json()["id"]

    f1_resp = await client.post("/v1/api/files/upload/init", json={"original_name": "f1.txt", "size": 1, "mime_type": "text/plain", "parts_count": 1, "folder_id": sub1_id})
    f1_id = f1_resp.json()["file_id"]

    f2_resp = await client.post("/v1/api/files/upload/init", json={"original_name": "f2.txt", "size": 1, "mime_type": "text/plain", "parts_count": 1, "folder_id": sub2_id})
    f2_id = f2_resp.json()["file_id"]

    await client.patch(f"/v1/api/folders/{root_id}/access", json={"set_access_level": 1})
    await recalculate_folder_access(uuid.UUID(root_id), db_session)

    root_contents = await client.get(f"/v1/api/folders/{root_id}/contents")
    s1 = next(f for f in root_contents.json()["folders"] if f["id"] == sub1_id)
    assert s1["actual_access_level"] == 2 

    s2 = next(f for f in root_contents.json()["folders"] if f["id"] == sub2_id)
    assert s2["actual_access_level"] == 1 

    f1_contents = await client.get(f"/v1/api/folders/{sub1_id}/contents")
    file1 = next(f for f in f1_contents.json()["files"] if f["id"] == f1_id)
    assert file1["actual_access_level"] == 2

    f2_contents = await client.get(f"/v1/api/folders/{sub2_id}/contents")
    file2 = next(f for f in f2_contents.json()["files"] if f["id"] == f2_id)
    assert file2["actual_access_level"] == 1
