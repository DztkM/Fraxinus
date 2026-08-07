import pytest
from unittest.mock import AsyncMock
import uuid

from main import app
from core.minio import get_s3_client

@pytest.mark.asyncio
async def test_init_upload(client, mock_s3):
    request_data = {
        "original_name": "test_image.png",
        "size": 8 * 1024 * 1024,
        "mime_type": "image/png",
        "parts_count": 2,
    }
    response = await client.post("/v1/api/files/upload/init", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "file_id" in data
    assert data["upload_id"] == "test_upload_id"
    assert "1" in data["presigned_urls"]
    assert "2" in data["presigned_urls"]
    
    mock_s3.create_multipart_upload.assert_called_once()
    assert mock_s3.generate_presigned_url.call_count == 2

@pytest.mark.asyncio
async def test_complete_upload(client, mock_s3):
    # 1. Init upload
    init_data = {
        "original_name": "complete_me.txt",
        "size": 100,
        "mime_type": "text/plain",
        "parts_count": 1,
    }
    init_resp = await client.post("/v1/api/files/upload/init", json=init_data)
    file_id = init_resp.json()["file_id"]
    
    # 2. Complete upload
    complete_data = {
        "upload_id": "test_upload_id",
        "parts": [{"PartNumber": 1, "ETag": "etag123"}]
    }
    complete_resp = await client.post(f"/v1/api/files/{file_id}/upload/complete", json=complete_data)
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "success"
    
    mock_s3.complete_multipart_upload.assert_called_once()

@pytest.mark.asyncio
async def test_download_file(client, mock_s3):
    # 1. Init
    init_resp = await client.post("/v1/api/files/upload/init", json={
        "original_name": "download_me.pdf",
        "size": 100,
        "mime_type": "application/pdf",
        "parts_count": 1
    })
    file_id = init_resp.json()["file_id"]
    
    # 2. Complete
    await client.post(f"/v1/api/files/{file_id}/upload/complete", json={
        "upload_id": "test_upload_id",
        "parts": [{"PartNumber": 1, "ETag": "etag"}]
    })
    
    # 3. Download
    download_resp = await client.get(f"/v1/api/files/{file_id}/download")
    assert download_resp.status_code == 200
    assert download_resp.json()["url"] == "http://mock-minio-url/presigned"
    assert download_resp.json()["original_name"] == "download_me.pdf"

@pytest.mark.asyncio
async def test_list_files(client, mock_s3):
    await client.post("/v1/api/files/upload/init", json={
        "original_name": "file1.txt", "size": 10, "mime_type": "text/plain", "parts_count": 1
    })
    await client.post("/v1/api/files/upload/init", json={
        "original_name": "file2.txt", "size": 10, "mime_type": "text/plain", "parts_count": 1
    })
    
    response = await client.get("/v1/api/files/")
    assert response.status_code == 200
    assert len(response.json()) >= 2

@pytest.mark.asyncio
async def test_delete_file(client, mock_s3):
    init_resp = await client.post("/v1/api/files/upload/init", json={
        "original_name": "delete_me.txt",
        "size": 10,
        "mime_type": "text/plain",
        "parts_count": 1
    })
    file_id = init_resp.json()["file_id"]
    
    del_resp = await client.delete(f"/v1/api/files/{file_id}")
    assert del_resp.status_code == 204
    
    mock_s3.delete_object.assert_called_once()

@pytest.mark.asyncio
async def test_update_file(client, mock_s3):
    init_resp = await client.post("/v1/api/files/upload/init", json={
        "original_name": "old_name.txt",
        "size": 10,
        "mime_type": "text/plain",
        "parts_count": 1
    })
    file_id = init_resp.json()["file_id"]
    
    update_resp = await client.patch(f"/v1/api/files/{file_id}", json={"original_name": "new_name.txt"})
    assert update_resp.status_code == 200
    assert update_resp.json()["original_name"] == "new_name.txt"

@pytest.mark.asyncio
async def test_access_deleted_file(client, mock_s3):
    # 1. Create file
    init_resp = await client.post("/v1/api/files/upload/init", json={
        "original_name": "delete_and_access_me.txt",
        "size": 10,
        "mime_type": "text/plain",
        "parts_count": 1
    })
    file_id = init_resp.json()["file_id"]
    
    # 2. Delete file
    await client.delete(f"/v1/api/files/{file_id}")
    
    # 3. Try to download
    download_resp = await client.get(f"/v1/api/files/{file_id}/download")
    assert download_resp.status_code == 404
