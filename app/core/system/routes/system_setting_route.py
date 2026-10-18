from fastapi import APIRouter, Depends, Request, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.database.db import get_db
from app.core.system.services.system_setting_service import SystemSettingService
from app.core.system.types.system_setting_types import CreateSystemSetting, UpdateSystemSetting

system_setting_router = APIRouter()

@system_setting_router.post("/", response_model=dict)
async def create_system_setting(data: CreateSystemSetting, db: AsyncSession = Depends(get_db)):
    service = SystemSettingService(db)
    setting = await service.create_system_setting(data)
    return JSONResponse(status_code=201, content=setting)

@system_setting_router.get("/{setting_id}", response_model=dict)
async def get_system_setting(setting_id: str, db: AsyncSession = Depends(get_db)):
    service = SystemSettingService(db)
    setting = await service.get_system_setting(setting_id)
    return JSONResponse(status_code=200, content=setting)

@system_setting_router.put("/{setting_id}", response_model=dict)
async def update_system_setting(setting_id: str, data: UpdateSystemSetting, db: AsyncSession = Depends(get_db)):
    service = SystemSettingService(db)
    updated = await service.update_system_setting(setting_id, data)
    return JSONResponse(status_code=200, content=updated)

@system_setting_router.delete("/{setting_id}", response_model=dict)
async def delete_system_setting(setting_id: str, db: AsyncSession = Depends(get_db)):
    service = SystemSettingService(db)
    await service.delete_system_setting(setting_id)
    return JSONResponse(status_code=204, content={"message": "System setting deleted successfully"})

@system_setting_router.get("/", response_model=dict)
async def list_system_settings(db: AsyncSession = Depends(get_db)):
    service = SystemSettingService(db)
    settings = await service.list_system_settings()
    return JSONResponse(status_code=200, content=settings) 