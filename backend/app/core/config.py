import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Default to a local dev DB if not provided
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://admin:CHANGEMELATER@localhost:5433/fraxinus_database")

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True, extra="ignore")

settings = Settings()
