from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.system.models.system_setting import SystemSettingModel
from app.core.system.types.system_setting_types import (
    CreateSystemSetting,
    UpdateSystemSetting,
)
from app.utils.crud.migration_helper import HybridCrudService as CrudService
from app.utils.crud.types_crud import response_message


class SystemSettingService:
    def __init__(self, db: AsyncSession):
        self.crud_service = CrudService(db=db, model=SystemSettingModel)
        self.db = db

    async def create_system_setting(self, data: CreateSystemSetting):
        try:
            setting = await self.crud_service.create(data=dict(data))
            return setting
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="System setting not created"))

    async def get_system_setting(self, setting_id: str):
        try:
            setting = await self.crud_service.get_one({"id": setting_id})
            return setting
        except Exception as e:
            raise HTTPException(status_code=404, detail=response_message(error=str(e), success_status=False, message="System setting not found"))

    async def update_system_setting(self, setting_id: str, data: UpdateSystemSetting):
        try:
            updated = await self.crud_service.update(filter={"id": setting_id}, data=dict(data))
            return updated
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="System setting not updated"))

    async def delete_system_setting(self, setting_id: str):
        try:
            await self.crud_service.delete({"id": setting_id})
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="System setting not deleted"))

    async def list_system_settings(self, filter: dict|None = None, query: dict|None = None):
        try:
            settings = await self.crud_service.get_many(query=query or {}, filter=filter or {})
            return settings
        except Exception as e:
            raise HTTPException(status_code=400, detail=response_message(error=str(e), success_status=False, message="System settings not found"))

    # Placeholder for RBAC
    async def require_access(self, user_id: str, scope_id: str | None = None):
        pass 