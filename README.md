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
```
alembic upgrade head
```