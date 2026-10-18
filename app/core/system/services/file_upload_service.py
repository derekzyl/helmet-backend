from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system.models.file_upload import FileUploadModel
from app.core.system.types.file_upload_types import CreateFileUpload, UpdateFileUpload
from app.utils.crud.migration_helper import HybridCrudService as CrudService
from app.utils.crud.types_crud import response_message


class FileUploadService:
    def __init__(self, db: AsyncSession):
        self.crud_service = CrudService(db=db, model=FileUploadModel)
        self.db = db

    async def create_file_upload(self, data: CreateFileUpload):
        try:
            file_upload = await self.crud_service.create(data=dict(data))
            return file_upload
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="File upload not created"))

    async def get_file_upload(self, file_upload_id: str):
        try:
            file_upload = await self.crud_service.get_one({"id": file_upload_id})
            return file_upload
        except Exception as e:
            raise HTTPException(status_code=404, detail=response_message(error=str(e), success_status=False, message="File upload not found"))

    async def update_file_upload(self, file_upload_id: str, data: UpdateFileUpload):
        try:
            updated = await self.crud_service.update(filter={"id": file_upload_id}, data=dict(data))
            return updated
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="File upload not updated"))

    async def delete_file_upload(self, file_upload_id: str):
        try:
            await self.crud_service.delete({"id": file_upload_id})
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="File upload not deleted"))

    async def list_file_uploads(self, filter: dict|None = None, query: dict|None = None):
        try:
            file_uploads = await self.crud_service.get_many(query=query or {}, filter=filter or {})
            return file_uploads
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="File uploads not found"))

    # Placeholder for RBAC
    async def require_access(self, user_id: str, entity_id: str):
        pass 