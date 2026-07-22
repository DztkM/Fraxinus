import os
import sys
import math
import requests

CHUNK_SIZE = 5 * 1024 * 1024  # 5Mb is minimum for MinIO multipart

def test_multipart_upload(token: str, file_path: str, folder_id: str = None):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    file_size = os.path.getsize(file_path)
    file_name = os.path.basename(file_path)
    parts_count = math.ceil(file_size / CHUNK_SIZE) or 1
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    print(f"1. Initiating upload for {file_name} ({file_size} bytes, {parts_count} parts)...")
    json_payload = {
        "original_name": file_name,
        "size": file_size,
        "mime_type": "application/octet-stream",
        "parts_count": parts_count
    }
    if folder_id:
        json_payload["folder_id"] = folder_id

    init_res = requests.post(
        "http://127.0.0.1:8000/api/files/upload/init",
        headers=headers,
        json=json_payload
    )

    if init_res.status_code != 200:
        print(f"Failed to init upload: {init_res.status_code} {init_res.text}")
        return

    init_data = init_res.json()
    file_id = init_data["file_id"]
    upload_id = init_data["upload_id"]
    urls = init_data["presigned_urls"]
    
    print(f"   -> File ID: {file_id}, Upload ID: {upload_id}")

    # 2. Upload parts
    print("2. Uploading parts...")
    completed_parts = []
    
    with open(file_path, "rb") as f:
        for part_number in range(1, parts_count + 1):
            chunk_data = f.read(CHUNK_SIZE)
            url = urls[str(part_number)]
            print(f"   -> Uploading part {part_number}/{parts_count}...")
            
            put_res = requests.put(url, data=chunk_data)
            if put_res.status_code != 200:
                print(f"Failed to upload part {part_number}: {put_res.status_code} {put_res.text}")
                return
            
            etag = put_res.headers.get("ETag")
            completed_parts.append({
                "PartNumber": part_number,
                "ETag": etag
            })

    # 3. Complete upload
    print("3. Completing upload...")
    complete_res = requests.post(
        f"http://127.0.0.1:8000/api/files/{file_id}/upload/complete",
        headers=headers,
        json={
            "upload_id": upload_id,
            "parts": completed_parts
        }
    )

    if complete_res.status_code == 200:
        print("Upload completed successfully!")
    else:
        print(f"Failed to complete upload: {complete_res.status_code} {complete_res.text}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: uv run python test_upload.py <jwt_token> <file_path> [folder_id]")
        sys.exit(1)
        
    token = sys.argv[1]
    file_path = sys.argv[2]
    folder_id = sys.argv[3] if len(sys.argv) > 3 else None
    
    test_multipart_upload(token, file_path, folder_id)
