from typing import Annotated, Any, Dict

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database.db import get_db
from app.core.auth.services.service_auth import AuthService
from app.core.auth.services.service_token import TokenService
from app.core.auth.types.types_auth import (
    ChangePassWordData,
    ResetPassWordData,
    VerifyEmailData,
    VerifyEmailDataTokenData,
)
from app.core.users.models.model_user import UserModel
from app.core.users.services.service_user import UserService
from app.core.users.types.type_user import (
    CreateUserData,
    ForgotPasswordData,
    LoginUserData,
    RefreshTokenData,
    UserData,
    UserTypeEnum,
)
from app.utils.crud.types_crud import response_message
from app.utils.logger import log

auth_router = APIRouter()


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_data: CreateUserData,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Create a new user account and send email verification."""
    try:
        if not user_data.get("user_type"):
            user_data = {**user_data, "user_type": UserTypeEnum.USER.value}

        auth_service = AuthService(db)
        result = await auth_service.create_user_auth(
            user_data, background_tasks=background_tasks
        )

        if result and hasattr(result, "id"):
            background_tasks.add_task(
                auth_service.send_email_verification,
                {"email": result.email},
                background_tasks,
            )

        user_dict = result.__dict__.copy() if hasattr(result, "__dict__") else {}
        user_dict.pop("password", None)
        user_dict.pop("_sa_instance_state", None)

        tokens = await TokenService.generate_auth_token(result.id, db=db)

        return {
            "success": True,
            "message": "User created successfully. Verification email sent.",
            "data": {"user": user_dict, "tokens": tokens},
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response_message(
                error="Registration failed - " + str(e),
                success_status=False,
                message="An error occurred during registration",
            ),
        )


@auth_router.post("/login", name="AUTH API")
async def login_user(
    data: Annotated[LoginUserData, Body()], db: AsyncSession = Depends(get_db)
):
    user = AuthService(db=db)
    login_result = await user.login_user(data={**data})
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder(login_result)
    )


@auth_router.post("/logout")
async def logout_user(
    db: AsyncSession = Depends(get_db),
    refresh_token: str = Depends(TokenService.get_refresh_token),
) -> Dict[str, Any]:
    auth_service = AuthService(db)
    try:
        result = await auth_service.logout(refresh_token)
        return {
            "success": result["success_status"],
            "message": result["message"],
            "data": result["data"],
        }
    except Exception:
        return {
            "success": True,
            "message": "Logged out successfully",
            "data": "You have been logged out",
        }


@auth_router.post("/refresh-token")
async def refresh_token(
    refresh_token: RefreshTokenData,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    auth_service = AuthService(db)
    try:
        result = await auth_service.refresh_token(refresh_token["refreshToken"])
        return {"success": True, "message": result["message"], "data": result["tokens"]}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=response_message(
                error="Token refresh failed",
                success_status=False,
                message="Unable to refresh authentication tokens",
            ),
        )


@auth_router.post("/forgot-password", name="AUTH API")
async def forgot_password(
    data: Annotated[ForgotPasswordData, Body()],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = AuthService(db=db)
    result = await user.forgot_password(
        data={**data}, background_tasks=background_tasks
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder(result)
    )


@auth_router.get("/me")
async def get_logged_in_user_info(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(UserService.get_logged_in_user),
) -> Dict[str, Any]:
    auth_service = AuthService(db)
    try:
        user_data = await auth_service.get_user_by_id(current_user["id"])
        if not user_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=response_message(
                    error="User not found",
                    success_status=False,
                    message="User account not found",
                ),
            )

        user: UserModel = user_data.get("data")
        user_dict = user.copy() if isinstance(user, dict) else user.to_dict()
        user_dict.pop("password", None)
        user_dict.pop("_sa_instance_state", None)

        return {
            "success": True,
            "message": "User information retrieved successfully",
            "data": user_dict,
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response_message(
                error="Failed to retrieve user information",
                success_status=False,
                message="An error occurred while retrieving user information",
            ),
        )


@auth_router.get("/permissions")
async def get_user_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(UserService.get_logged_in_user),
) -> Dict[str, Any]:
    try:
        user_service = UserService(db)
        permissions = await user_service.get_user_permissions(current_user["id"])
        permission_strings = [f"{perm.resource}_{perm.action}" for perm in permissions]
        return {
            "success": True,
            "message": "User permissions retrieved successfully",
            "data": permission_strings,
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response_message(
                error="Failed to retrieve user permissions",
                success_status=False,
                message="An error occurred while retrieving user permissions",
            ),
        )


@auth_router.get("/health")
async def health_check() -> Dict[str, Any]:
    return {
        "success": True,
        "message": "Authentication service is healthy",
        "data": {"service": "auth", "status": "operational"},
    }


@auth_router.post("/reset-password", name="AUTH API", summary="Reset user password")
async def reset_password(
    data: ResetPassWordData,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = AuthService(db=db)
    result = await user.reset_password(data=data, background_tasks=background_tasks)
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder(result)
    )


@auth_router.post("/verify-email", name="AUTH API", summary="Verify user email")
async def verify_email(
    data: VerifyEmailDataTokenData,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = AuthService(db=db)
    result = await user.verify_email(data=data, background_tasks=background_tasks)
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder(result)
    )


@auth_router.post("/send-verification-email")
async def send_verification_email(
    verification_data: VerifyEmailData,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    auth_service = AuthService(db)
    try:
        result = await auth_service.send_email_verification(
            verification_data, background_tasks
        )
        return {
            "success": result["success_status"],
            "message": result["message"],
            "data": result["data"],
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=response_message(
                error="Failed to send verification email",
                success_status=False,
                message="An error occurred while sending verification email",
            ),
        )


@auth_router.post("/change-password", name="AUTH API", summary="Change user password")
async def change_password(
    data: ChangePassWordData,
    user_id: Annotated[UserData, Depends(UserService.get_logged_in_user)],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = AuthService(db=db)
    payload = dict(data)
    current_password = payload.get("current_password") or payload.get("old_password")
    result = await user.change_password(
        data={
            **payload,
            "user_id": user_id["id"],
            "current_password": current_password,
        },
        background_tasks=background_tasks,
    )
    log.logs.info(f"Password changed: {result}")
    return JSONResponse(
        status_code=status.HTTP_200_OK, content=jsonable_encoder(result)
    )
