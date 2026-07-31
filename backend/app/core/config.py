import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Default to a local dev DB if not provided
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:CHANGEMELATER@localhost:5433/fraxinus_database")

    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
    MINIO_EXTERNAL_ENDPOINT: str = os.getenv("MINIO_EXTERNAL_ENDPOINT", "http://127.0.0.1:9000")
    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER", "minioadmin")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD", "CHANGEMELATER")
    MINIO_BUCKET_NAME: str = os.getenv("MINIO_BUCKET_NAME", "fraxinus-files")

    # Clerk
    CLERK_FRONTEND_API: str = os.getenv("CLERK_FRONTEND_API", "https://relaxed-mustang-84.clerk.accounts.dev")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGEMELATERCHANGEMELATERCHANGEMELATERCHANGEMELATERCHANGEMELATE")

    # Admin
    ADMIN_USER_ID: str | None = os.getenv("ADMIN_USER_ID", "user_3HHJrGbhDEloLXWG3vzk73NihXG")

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

settings = Settings()
