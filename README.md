# Internal File Gateway

## How to run

create .env
```
cp .env.example .env
```

### prod version

```bash
docker compose -f compose.yaml up -d
```

### dev version

```bash
docker compose -f compose.dev.yaml up -d
cd backend
uv sync
uv run fastapi dev app/main.py 
```

Links:
- FastAPI backend docs: http://localhost:8000/docs
- MinIO WebUI: http://127.0.0.1:9001/


```bash
docker compose down -v 
```

## Migrations
```bash
alembic upgrade head
```

## Testing Multipart Upload
To test multipart upload and file endpoints a test script is provided.

1. Start Docker containers (`compose.dev.yaml`) and the FastAPI backend.
2. Get a valid JWT token from Clerk.
3. Run the test script from the `backend` folder:
```bash
cd backend
uv run python scripts/test_upload.py "<YOUR_JWT_TOKEN>" "path/to/any/file.jpg"
```
This script will:
- Contact `/api/files/upload/init` to create DB records and get pre-signed MinIO URLs for 5MB chunks.
- Upload each chunk directly to MinIO.
- Contact `/api/files/{file_id}/upload/complete` to finish the upload.

You can then view the uploaded files in the MinIO WebUI (credentials in `.env`) or test the download endpoint via Swagger (`http://localhost:8000/docs`).