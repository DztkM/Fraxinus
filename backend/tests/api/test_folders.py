import pytest

@pytest.mark.asyncio
async def test_create_folder(client):
    response = await client.post("/v1/api/folders/", json={"name": "My New Folder"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "My New Folder"
    assert "id" in data
    
@pytest.mark.asyncio
async def test_create_nested_folder(client):
    # 1. Create parent
    parent_response = await client.post("/v1/api/folders/", json={"name": "Parent Folder"})
    parent_id = parent_response.json()["id"]
    
    # 2. Create child
    child_response = await client.post("/v1/api/folders/", json={"name": "Child Folder", "parent_id": parent_id})
    assert child_response.status_code == 200
    child_data = child_response.json()
    assert child_data["parent_id"] == parent_id

@pytest.mark.asyncio
async def test_list_root_contents(client):
    await client.post("/v1/api/folders/", json={"name": "Root Folder 1"})
    await client.post("/v1/api/folders/", json={"name": "Root Folder 2"})
    
    response = await client.get("/v1/api/folders/root/contents")
    assert response.status_code == 200
    data = response.json()
    
    assert "folders" in data
    assert "files" in data
    assert len(data["folders"]) >= 2

@pytest.mark.asyncio
async def test_rename_folder(client):
    create_resp = await client.post("/v1/api/folders/", json={"name": "Old Name"})
    folder_id = create_resp.json()["id"]
    
    rename_resp = await client.patch(f"/v1/api/folders/{folder_id}", json={"name": "New Name"})
    assert rename_resp.status_code == 200
    assert rename_resp.json()["name"] == "New Name"

@pytest.mark.asyncio
async def test_delete_folder(client):
    create_resp = await client.post("/v1/api/folders/", json={"name": "To Be Deleted"})
    folder_id = create_resp.json()["id"]
    
    del_resp = await client.delete(f"/v1/api/folders/{folder_id}")
    assert del_resp.status_code == 204

@pytest.mark.asyncio
async def test_delete_folder_with_files(client, mock_s3):
    # Create parent folder
    folder_resp = await client.post("/v1/api/folders/", json={"name": "Folder with file"})
    folder_id = folder_resp.json()["id"]
    
    # Init upload of a file to this folder
    init_data = {
        "original_name": "file_in_folder.txt",
        "size": 100,
        "mime_type": "text/plain",
        "parts_count": 1,
        "folder_id": folder_id
    }
    init_resp = await client.post("/v1/api/files/upload/init", json=init_data)
    assert init_resp.status_code == 200
    
    # Try deleting parent folder
    del_resp = await client.delete(f"/v1/api/folders/{folder_id}")
    assert del_resp.status_code == 400
    assert "contains files" in del_resp.json()["detail"]

@pytest.mark.asyncio
async def test_access_deleted_folder(client):
    folder_resp = await client.post("/v1/api/folders/", json={"name": "To Be Deleted And Accessed"})
    folder_id = folder_resp.json()["id"]
    
    await client.delete(f"/v1/api/folders/{folder_id}")
    
    # Try to access it
    get_resp = await client.get(f"/v1/api/folders/{folder_id}/contents")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_folder_with_subfolder(client):
    # 1. Create parent folder
    parent_response = await client.post("/v1/api/folders/", json={"name": "Parent Folder"})
    parent_id = parent_response.json()["id"]
    
    # 2. Create child folder
    child_response = await client.post("/v1/api/folders/", json={"name": "Child Folder", "parent_id": parent_id})
    
    # 3. Try deleting parent folder
    del_resp = await client.delete(f"/v1/api/folders/{parent_id}")
    assert del_resp.status_code == 400
    assert "contains folders" in del_resp.json()["detail"]