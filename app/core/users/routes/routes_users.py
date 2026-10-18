from typing import Annotated

from fastapi import APIRouter, Depends, Path
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.users.services.service_user import UserService
from app.core.users.types.type_user import CreateUserData, UpdateUserData

user_router = APIRouter()

@user_router.post("/", response_model=dict)
async def create_user(
    data: CreateUserData,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await UserService(db=db).create_user(user_data=data)
    return JSONResponse(status_code=201, content=user)





@user_router.get("/profile")
async def get_profile(
    user_id: Annotated[str, Depends(UserService.get_logged_in_user)],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    return JSONResponse(status_code=200, content=user_id)

@user_router.get("/{user_id}")
async def get_user_by_id(
    user_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await UserService(db=db).get_user_by_id(user_id=user_id)
    return JSONResponse(status_code=200, content=user)


@user_router.put("/{user_id}")
async def update_user(
    user_id: Annotated[str, Path()],
    data: UpdateUserData,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    user = await UserService(db=db).update_user(filter={"id": user_id}, data=data)
    return JSONResponse(status_code=200, content=user)

@user_router.delete("/{user_id}")
async def delete_user(
    user_id: Annotated[str, Path()],
    db: Annotated[AsyncSession, Depends(get_db)]
):
    await UserService(db=db).delete_user(user_id=user_id)
    return JSONResponse(status_code=204,    content={"message": "User deleted successfully"})