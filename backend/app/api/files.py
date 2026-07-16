import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.minio import get_s3_client
from core.auth import get_current_user
from models.file import File
from models.folder import Folder
from models.physical_file import PhysicalFile
from schemas.file import (
    FileUploadInitRequest,
    FileUploadInitResponse,
    FileUploadCompleteRequest,
    FileResponse,
    FileDownloadResponse,
)

router = APIRouter(prefix="/api/files", tags=["files"])

@router.post("/upload/init", response_model=FileUploadInitResponse)
async def init_upload(
    request: FileUploadInitRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    s3: Any = Depends(get_s3_client),
):
    file_id = uuid.uuid4()
    path = str(file_id).replace("-", "_")
    
    if request.folder_id:
        folder_result = await db.execute(select(Folder).where(Folder.id == request.folder_id))
        folder = folder_result.scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")
        if folder.author_id != user_id:
            raise HTTPException(status_code=403, detail="Access denied") #TODO change to 404 in prod
        if folder.path:
            path = f"{folder.path}.{path}"

    internal_key = str(uuid.uuid4())
    
    # Start multipart upload in MinIO
    response = await s3.create_multipart_upload(
        Bucket=settings.MINIO_BUCKET_NAME,
        Key=internal_key,
        ContentType=request.mime_type
    )
    upload_id = response["UploadId"]
    
    # Generate presigned URLs for parts
    presigned_urls = {}
    for i in range(1, request.parts_count + 1):
        url = await s3.generate_presigned_url(
            "upload_part",
            Params={
                "Bucket": settings.MINIO_BUCKET_NAME,
                "Key": internal_key,
                "UploadId": upload_id,
                "PartNumber": i,
            },
            ExpiresIn=3600,
        )
        # Fix URL for external access (from host machine instead of docker network)
        if settings.MINIO_EXTERNAL_ENDPOINT:
            url = url.replace(settings.MINIO_ENDPOINT, settings.MINIO_EXTERNAL_ENDPOINT, 1)
        presigned_urls[i] = url
        
    # db records
    pf = PhysicalFile(
        internal_key=internal_key,
        file_hash="none",  # TODO change Dummy value later
        size=request.size,
        mime_type=request.mime_type,
    )
    db.add(pf)
    await db.flush()  # to get pf.id
    
    file_record = File(
        id=file_id,
        folder_id=request.folder_id,
        original_name=request.original_name,
        path=path,
        uploader_id=user_id,
        status="pending",
        physical_file_id=pf.id,
    )
    db.add(file_record)
    await db.commit()
    await db.refresh(file_record)
    
    return FileUploadInitResponse(
        file_id=file_record.id,
        upload_id=upload_id,
        presigned_urls=presigned_urls,
    )

@router.post("/{file_id}/upload/complete")
async def complete_upload(
    file_id: uuid.UUID,
    request: FileUploadCompleteRequest,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    s3: Any = Depends(get_s3_client),
):
    # Get File record
    result = await db.execute(select(File).where(File.id == file_id))
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
        
    if file_record.uploader_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied") # TODO change to 404 later
        
    # Get PhysicalFile
    pf_result = await db.execute(select(PhysicalFile).where(PhysicalFile.id == file_record.physical_file_id))
    pf = pf_result.scalar_one()
    
    # Complete multipart upload in MinIO
    parts = [{"PartNumber": p.PartNumber, "ETag": p.ETag} for p in request.parts]
    
    try:
        await s3.complete_multipart_upload(
            Bucket=settings.MINIO_BUCKET_NAME,
            Key=pf.internal_key,
            UploadId=request.upload_id,
            MultipartUpload={"Parts": parts}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")
        
    # Update File status
    file_record.status = "completed"
    await db.commit()
    
    return {"status": "success"}

@router.get("/{file_id}/download", response_model=FileDownloadResponse)
async def download_file(
    file_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    s3: Any = Depends(get_s3_client),
):
    result = await db.execute(select(File).where(File.id == file_id))
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
        
    if file_record.uploader_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied") # TODO change to 404 later
        
    pf_result = await db.execute(select(PhysicalFile).where(PhysicalFile.id == file_record.physical_file_id))
    pf = pf_result.scalar_one()
    
    # Generate pre-signed URL for downloading
    url = await s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.MINIO_BUCKET_NAME,
            "Key": pf.internal_key,
            "ResponseContentDisposition": f'attachment; filename="{file_record.original_name}"'
        },
        ExpiresIn=3600,
    )
    
    # Fix URL for external access
    if settings.MINIO_EXTERNAL_ENDPOINT:
        url = url.replace(settings.MINIO_ENDPOINT, settings.MINIO_EXTERNAL_ENDPOINT, 1)
    
    return FileDownloadResponse(url=url, original_name=file_record.original_name)

@router.get("/", response_model=list[FileResponse])
async def list_files(
    limit: int = 100,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(File).where(File.uploader_id == user_id).limit(limit)
    )
    files = result.scalars().all()
    return files

@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_file(
    file_id: uuid.UUID,
    user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    s3: Any = Depends(get_s3_client),
):
    result = await db.execute(select(File).where(File.id == file_id))
    file_record = result.scalar_one_or_none()
    
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found")
        
    if file_record.uploader_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied") #TODO change to 404 in prod
        
    physical_file_id = file_record.physical_file_id
    
    await db.delete(file_record)
    await db.flush()
    
    # Check if physical file is still referenced
    other_files_result = await db.execute(
        select(File).where(File.physical_file_id == physical_file_id).limit(1)
    )
    other_files = other_files_result.scalars().first()
    
    if not other_files:
        pf_result = await db.execute(select(PhysicalFile).where(PhysicalFile.id == physical_file_id))
        pf = pf_result.scalar_one_or_none()
        if pf:
            try:
                await s3.delete_object(Bucket=settings.MINIO_BUCKET_NAME, Key=pf.internal_key)
            except Exception:
                pass
            await db.delete(pf)
            
    await db.commit()
    return None
