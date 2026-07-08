import logging
from contextlib import asynccontextmanager

import aioboto3
from botocore.exceptions import ClientError

from core.config import settings

logger = logging.getLogger(__name__)

session = aioboto3.Session()

async def get_s3_client():
    async with session.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ROOT_USER,
        aws_secret_access_key=settings.MINIO_ROOT_PASSWORD,
    ) as client:
        yield client

async def init_minio_bucket():
    """Ensure the default bucket exists on startup."""
    async with asynccontextmanager(get_s3_client)() as s3:
        try:
            await s3.head_bucket(Bucket=settings.MINIO_BUCKET_NAME)
            logger.info(f"Bucket '{settings.MINIO_BUCKET_NAME}' already exists.")
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "404":
                # Bucket does not exist, create it
                await s3.create_bucket(Bucket=settings.MINIO_BUCKET_NAME)
                logger.info(f"Bucket '{settings.MINIO_BUCKET_NAME}' created.")
            else:
                logger.error(f"Error checking bucket: {e}")
                raise
