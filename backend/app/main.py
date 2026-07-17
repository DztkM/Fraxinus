import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine

from core.auth import get_current_user
from api.files import router as files_router
from api.folders import router as folders_router
from api.shared import router as shared_router
from core.minio import init_minio_bucket

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_minio_bucket()
    yield

app = FastAPI(lifespan=lifespan)
app.include_router(files_router)
app.include_router(folders_router)
app.include_router(shared_router)

DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:CHANGEMELATER@localhost:5433/fraxinus_database")



engine = None
if DATABASE_URL:
    engine = create_async_engine(DATABASE_URL)

@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    db_status = "not configured"

    if engine is not None:
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
        except SQLAlchemyError as e:
            db_status = f"error: {e.__class__.__name__}"

    return {
        "status": "ok",
        "database": db_status,
        "database_url": os.getenv("DATABASE_URL", "Not Set").split("@")[-1],
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "Not Set"),
    }

@app.get("/v1/api/check_auth")
async def check_auth(user_id: str | None = Depends(get_current_user)):
    if user_id is None:
        return {"message": "Access granted via share_token"}
        
    return {
        "message": "Authentication successful",
        "user_id": user_id
    }