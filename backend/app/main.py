import os
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "database_url": os.getenv("DATABASE_URL", "Not Set").split("@")[-1], 
        "minio_endpoint": os.getenv("MINIO_ENDPOINT", "Not Set")
    }