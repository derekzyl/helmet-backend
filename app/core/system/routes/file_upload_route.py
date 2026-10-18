from fastapi import APIRouter, Depends, Request, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database.db import get_db
from app.core.system.services.file_upload_service import FileUploadService
from app.core.system.types.file_upload_types import CreateFileUpload, UpdateFileUpload

file_upload_router = APIRouter()

@file_upload_router.post("/", response_model=dict)
async def create_file_upload(data: CreateFileUpload, db: AsyncSession = Depends(get_db)):
    service = FileUploadService(db)
    file_upload = await service.create_file_upload(data)
    return JSONResponse(status_code=201, content=file_upload)

@file_upload_router.get("/{file_upload_id}", response_model=dict)
async def get_file_upload(file_upload_id: str, db: AsyncSession = Depends(get_db)):
    service = FileUploadService(db)
    file_upload = await service.get_file_upload(file_upload_id)
    return JSONResponse(status_code=200, content=file_upload)

@file_upload_router.put("/{file_upload_id}", response_model=dict)
async def update_file_upload(file_upload_id: str, data: UpdateFileUpload, db: AsyncSession = Depends(get_db)):
    service = FileUploadService(db)
    updated = await service.update_file_upload(file_upload_id, data)
    return JSONResponse(status_code=200, content=updated)

@file_upload_router.delete("/{file_upload_id}", response_model=dict)
async def delete_file_upload(file_upload_id: str, db: AsyncSession = Depends(get_db)):
    service = FileUploadService(db)
    await service.delete_file_upload(file_upload_id)
    return JSONResponse(status_code=204, content={"message": "File upload deleted successfully"})

@file_upload_router.get("/", response_model=dict)
async def list_file_uploads(db: AsyncSession = Depends(get_db)):
    service = FileUploadService(db)
    file_uploads = await service.list_file_uploads()
    return JSONResponse(status_code=200, content=file_uploads) 