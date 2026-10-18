from typing import Any, Dict, Optional, TypedDict

from fastapi import BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import env
from app.config.config import TokenType
from app.config.database.db import get_db
from app.core.auth.services.middleware_auth import response_message
from app.core.auth.services.service_token import TokenService
from app.core.auth.types.types_auth import (
    ForgotPasswordData,
    LoginData,
    ResetPasswordData,
    VerifyEmailData,
    VerifyEmailDataTokenData,
    VerifyResetTokenData,
)
from app.core.roles.services.roles import RolePermissionService
from app.core.users.models.model_user import UserModel, UserModelType
from app.core.users.services.service_user import UserService
from app.core.users.types.type_user import CreateUserData, UserTypeEnum
from app.utils import password_hash
from app.utils.crud.types_crud import ResponseMessage
from app.utils.logger import log
from app.utils.mail import EmailTemplateTypesEnum as ET
from app.utils.mail import SMTPMailer
from app.utils.regex import email_regex, password_regex


def _normalize_email(email: str) -> str:
    return str(email or "").strip().lower()


def _user_record_email(user: Any) -> str:
    if hasattr(user, "email"):
        return str(user.email or "")
    if isinstance(user, dict):
        return str(user.get("email") or "")
    return ""


def _user_record_name(user: Any, fallback: str = "") -> str:
    if hasattr(user, "first_name") or hasattr(user, "last_name"):
        name = f"{getattr(user, 'first_name', '') or ''} {getattr(user, 'last_name', '') or ''}".strip()
        return name or fallback
    if isinstance(user, dict):
        name = f"{user.get('first_name') or ''} {user.get('last_name') or ''}".strip()
        return name or fallback
    return fallback


def _unwrap_user_model(user_data: Any) -> Any:
    if isinstance(user_data, dict) and user_data.get("data") is not None:
        return user_data["data"]
    return user_data


class OthersTypes(TypedDict):
    resource: str
    action: str
    name: str


class AuthService(UserService):
    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.db = db

    async def login_user(self, data: LoginData) -> Dict[str, Any]:
        try:
            if email_regex.match(data["email"]):
                user_data: ResponseMessage = await self.get_user(
                    {"email": str(data["email"]).lower().strip()}
                )
            else:
                user_data = await self.get_user(
                    {"username": str(data["email"]).lower().strip()}
                )

            if (
                not user_data
                or not isinstance(user_data, dict)
                or "data" not in user_data
                or not user_data["data"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Invalid credentials",
                        success_status=False,
                        message="Invalid email/username or password",
                    ),
                )

            user: UserModel = user_data["data"]
            user_dict = user if isinstance(user, dict) else user.to_dict()

            if user_dict.get("allow_login") is False:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Account disabled",
                        success_status=False,
                        message="This account cannot sign in. Contact support.",
                    ),
                )

            if not password_hash.PassHash().verify_me(
                password=data["password"], hashed_password=user_dict["password"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Invalid credentials",
                        success_status=False,
                        message="Invalid email/username or password",
                    ),
                )

            tokens = await TokenService.generate_auth_token(
                user_id=user_dict["id"], db=self.db
            )
            if isinstance(user_dict, dict):
                user_dict.pop("password", None)

            return {"user": user_dict, "tokens": tokens, "message": "Login successful"}

        except HTTPException:
            raise
        except Exception as e:
            log.logs.error(f"Error during login: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response_message(
                    error="Internal server error",
                    success_status=False,
                    message="An unexpected error occurred",
                ),
            )

    async def send_email_verification(
        self, data: VerifyEmailData, background_tasks: BackgroundTasks
    ) -> ResponseMessage:
        try:
            normalized_email = _normalize_email(data["email"])
            user = await self.get_user_by_email(normalized_email)
            otp_token = TokenService.generate_otp_token()

            await TokenService.save_token(
                data={
                    "user_id": user.id,
                    "token": str(otp_token),
                    "type": TokenType.VERIFY_EMAIL.value,
                    "expires": 180,
                    "blacklisted": False,
                },
                db=self.db,
            )

            if env.env["mail"]["use_mail_service"]:
                app_name = env.env.get("app_name", "FastAPI Starter")
                mailer = SMTPMailer(
                    background_tasks=background_tasks,
                    receiver_emails=[user.email],
                    template_name=ET.VERIFY_EMAIL,
                    subject=f"Verify Your Email Address - {app_name}",
                    template_data={
                        "name": getattr(user, "first_name", user.email),
                        "otp": otp_token,
                        "expiry_hours": 3,
                        "website_name": app_name,
                    },
                    background=False,
                )
                await mailer.send_mail()

            return response_message(
                success_status=True,
                message="Verification email sent successfully",
                data="Please check your email for the verification code",
            )
        except HTTPException:
            raise
        except Exception as e:
            log.logs.error(f"Error sending verification email: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response_message(
                    error="Internal server error",
                    success_status=False,
                    message="Failed to send verification email",
                ),
            )

    async def verify_reset_password_token(
        self, data: VerifyResetTokenData
    ) -> ResponseMessage:
        try:
            email = data.get("email")
            token = data.get("token")
            if not email or not token:
                return response_message(
                    success_status=False,
                    message="Validation failed",
                    error="Email and token are required",
                )

            user = await self.get_user_by_email(email)
            if not user:
                return response_message(
                    success_status=False,
                    message="Invalid token",
                    error="Invalid or expired reset token",
                )

            token_data = await TokenService.verify_otp_token(
                token=token,
                user_id=user.id,
                type=TokenType.RESET_PASSWORD,
                db=self.db,
            )
            if token_data:
                return response_message(
                    success_status=True,
                    message="Token verified successfully",
                    data={"valid": True, "user_id": user.id, "email": user.email},
                )
            return response_message(
                success_status=False,
                message="Invalid token",
                error="Invalid or expired reset token",
            )
        except HTTPException as e:
            error_detail = e.detail
            if isinstance(error_detail, dict):
                return response_message(
                    success_status=False,
                    message=error_detail.get("message", "Invalid token"),
                    error=error_detail.get("error", "Token verification failed"),
                )
            return response_message(
                success_status=False,
                message="Invalid token",
                error="Token verification failed",
            )
        except Exception as e:
            log.logs.error(f"Error in verify reset password token: {e}")
            return response_message(
                success_status=False,
                message="Invalid token",
                error="Token verification failed",
            )

    async def verify_email(
        self, data: VerifyEmailDataTokenData, background_tasks: BackgroundTasks
    ):
        try:
            user = await self.get_user_by_email(data["email"])
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=response_message(
                        error="User not found",
                        success_status=False,
                        message="User account not found",
                    ),
                )

            token_data = await TokenService.verify_otp_token(
                db=self.db,
                user_id=user.id,
                token=str(data["token"]).strip(),
                type=TokenType.VERIFY_EMAIL,
            )

            if not token_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Invalid token",
                        success_status=False,
                        message="Invalid or expired verification token",
                    ),
                )

            await self.db.execute(
                update(UserModel)
                .where(UserModel.id == user.id)
                .values(email_verified=True)
            )
            await self.db.commit()

            if env.env["mail"]["use_mail_service"]:
                app_name = env.env.get("app_name", "FastAPI Starter")
                mailer = SMTPMailer(
                    background_tasks=background_tasks,
                    receiver_emails=[user.email],
                    template_name=ET.WELCOME,
                    subject=f"Welcome to {app_name}",
                    template_data={
                        "name": getattr(user, "first_name", user.email),
                        "app_name": app_name,
                        "login_link": f"{env.env.get('frontend_url', '#')}/login",
                    },
                    background=True,
                )
                await mailer.send_mail()

            return response_message(
                success_status=True,
                message="Email verified successfully",
                data="Your email has been verified",
            )
        except HTTPException:
            raise
        except Exception as e:
            log.logs.error(f"Error in email verification: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response_message(
                    error="Email verification failed",
                    success_status=False,
                    message="An error occurred during email verification",
                ),
            )

    async def forgot_password(
        self, data: ForgotPasswordData, background_tasks: BackgroundTasks
    ) -> ResponseMessage:
        success_message = (
            "If you have an account, a password reset email has been sent"
        )
        try:
            normalized_email = _normalize_email(data["email"])
            try:
                user = await self.get_user_by_email(normalized_email)
            except HTTPException:
                user = None

            if user:
                reset_token = TokenService.generate_otp_token()
                await TokenService.save_token(
                    data={
                        "user_id": user.id,
                        "token": str(reset_token),
                        "type": TokenType.RESET_PASSWORD.value,
                        "expires": 30,
                        "blacklisted": False,
                    },
                    db=self.db,
                )
                if env.env["mail"]["use_mail_service"]:
                    app_name = env.env.get("app_name", "FastAPI Starter")
                    mailer = SMTPMailer(
                        background_tasks=background_tasks,
                        receiver_emails=[user.email],
                        template_name=ET.RESET_PASSWORD,
                        subject=f"Reset Your Password - {app_name}",
                        template_data={
                            "name": _user_record_name(user, user.email),
                            "otp": reset_token,
                            "expiry_hours": 0.5,
                        },
                        background=True,
                    )
                    await mailer.send_mail()

            return response_message(
                success_status=True, message="Reset email sent", data=success_message
            )
        except Exception as e:
            log.logs.error(f"Error in forgot password: {e}")
            return response_message(
                success_status=True,
                message="Reset email sent",
                data=success_message,
            )

    async def reset_password(
        self, data: ResetPasswordData, background_tasks: BackgroundTasks
    ) -> ResponseMessage:
        try:
            email = data.get("email")
            token = data.get("token")
            new_password = data.get("password")
            if not email or not token or not new_password:
                return response_message(
                    success_status=False,
                    message="Validation failed",
                    error="Email, token, and new password are required",
                )

            user_data = await self.get_user({"email": email})
            if not user_data:
                return response_message(
                    success_status=False,
                    message="Invalid request",
                    error="Invalid reset token",
                )

            user_model = user_data["data"]
            user_id = user_model.id if hasattr(user_model, "id") else user_model["id"]
            token_data = await TokenService.verify_otp_token(
                token=token,
                user_id=user_id,
                type=TokenType.RESET_PASSWORD,
                db=self.db,
            )
            if not token_data:
                return response_message(
                    success_status=False,
                    message="Invalid or expired reset token",
                    error="Invalid reset token",
                )

            hashed_password = password_hash.PassHash().hash_me(new_password)
            await self.db.execute(
                update(UserModel)
                .values(password=hashed_password)
                .where(UserModel.id == user_id)
            )
            await self.db.commit()

            if env.env["mail"]["use_mail_service"]:
                app_name = env.env.get("app_name", "FastAPI Starter")
                receiver_email = _user_record_email(user_model)
                mailer = SMTPMailer(
                    background_tasks=background_tasks,
                    receiver_emails=[receiver_email],
                    template_name=ET.PASSWORD_CHANGE,
                    subject=f"Password Changed Successfully - {app_name}",
                    template_data={
                        "name": _user_record_name(user_model, receiver_email),
                        "email": receiver_email,
                        "change_date": "now",
                        "support_email": env.env.get(
                            "support_email", "support@example.com"
                        ),
                    },
                    background=True,
                )
                await mailer.send_mail()

            return response_message(
                success_status=True,
                message="Password reset successful",
                data="Your password has been reset successfully",
            )
        except HTTPException as e:
            error_detail = e.detail
            if isinstance(error_detail, dict):
                return response_message(
                    success_status=False,
                    message=error_detail.get("message", "Invalid token"),
                    error=error_detail.get("error", "Password reset failed"),
                )
            return response_message(
                success_status=False,
                message="Invalid token",
                error="Password reset failed",
            )
        except Exception as e:
            log.logs.error(f"Error in reset password: {e}")
            return response_message(
                success_status=False,
                message="Password reset failed",
                error="An error occurred while resetting password",
            )

    async def change_password(
        self, data: Dict[str, Any], background_tasks: BackgroundTasks
    ) -> ResponseMessage:
        try:
            user_data = await self.get_user_by_id(data["user_id"])
            if not user_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=response_message(
                        error="User not found",
                        success_status=False,
                        message="User account not found",
                    ),
                )

            user = _unwrap_user_model(user_data)
            current_password = data.get("current_password") or data.get("old_password")
            user_password = (
                user["password"] if isinstance(user, dict) else user.password
            )
            if not current_password or not password_hash.PassHash().verify_me(
                password=current_password, hashed_password=user_password
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Invalid current password",
                        success_status=False,
                        message="Current password is incorrect",
                    ),
                )

            if not password_regex.match(data["new_password"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=response_message(
                        error="Invalid password format",
                        success_status=False,
                        message="Password must be 8+ characters with uppercase, lowercase, number, and special character",
                    ),
                )

            hashed_password = password_hash.PassHash().hash_me(data["new_password"])
            await self.db.execute(
                update(UserModel)
                .where(UserModel.id == data["user_id"])
                .values(password=hashed_password)
            )
            await self.db.commit()

            if env.env["mail"]["use_mail_service"]:
                app_name = env.env.get("app_name", "FastAPI Starter")
                receiver_email = _user_record_email(user)
                mailer = SMTPMailer(
                    background_tasks=background_tasks,
                    receiver_emails=[receiver_email],
                    template_name=ET.PASSWORD_CHANGE,
                    subject=f"Password Changed Successfully - {app_name}",
                    template_data={
                        "name": _user_record_name(user, receiver_email),
                        "email": receiver_email,
                        "change_date": "now",
                        "support_email": env.env.get(
                            "support_email", "support@example.com"
                        ),
                    },
                    background=True,
                )
                await mailer.send_mail()

            return response_message(
                success_status=True,
                message="Password changed successfully",
                data="Your password has been updated",
            )
        except HTTPException:
            raise
        except Exception as e:
            log.logs.error(f"Error changing password: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=response_message(
                    error="Password change failed",
                    success_status=False,
                    message="An error occurred while changing password",
                ),
            )

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        try:
            tokens = await TokenService.refresh_auth_token(refresh_token, db=self.db)
            return {"tokens": tokens, "message": "Tokens refreshed successfully"}
        except Exception as e:
            log.logs.error(f"Error refreshing token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=response_message(
                    error="Invalid refresh token",
                    success_status=False,
                    message="Unable to refresh tokens",
                ),
            )

    async def logout(self, refresh_token: str) -> ResponseMessage:
        try:
            await TokenService.verify_token(
                token=refresh_token, type=TokenType.REFRESH_TOKEN, db=self.db
            )
        except Exception as e:
            log.logs.error(f"Error during logout: {e}")
        return response_message(
            success_status=True,
            message="Logged out successfully",
            data="You have been logged out",
        )

    async def _get_user_by_email(self, email: str) -> Optional[UserModel]:
        stmt = select(UserModel).filter(UserModel.email == email)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def create_user_auth(
        self, user_data: CreateUserData, background_tasks: BackgroundTasks
    ):
        """Create a new user account."""
        if not user_data.get("user_type"):
            user_data = {**user_data, "user_type": UserTypeEnum.USER.value}
        return await super().create_user(user_data)


async def get_current_user(request: Request) -> UserModelType:
    user = getattr(request.state, "user", None)
    if not user:
        raise HTTPException(
            status_code=401,
            detail=response_message(
                error="User not authenticated",
                success_status=False,
                message="Authentication required",
            ),
        )
    return user


async def require_permission(
    permission_name: str,
    resource: str,
    action: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role_service = RolePermissionService(db)
    has_permission = await role_service.check_user_permission(
        user_id=current_user["id"],
        permission_name=permission_name,
        resource=resource,
        action=action,
    )
    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=response_message(
                error="Insufficient permissions",
                success_status=False,
                message=(
                    f"Permission '{permission_name}' required for "
                    f"resource '{resource}' and action '{action}'"
                ),
            ),
        )
    return current_user


async def check_permission(
    permission_name: str,
    resource: str,
    action: str,
    current_user: dict,
    db: AsyncSession,
    others: Optional[list[OthersTypes]] = None,
):
    role_service = RolePermissionService(db)
    has_permission = await role_service.check_user_permission(
        user_id=current_user["id"],
        permission_name=permission_name,
        resource=resource,
        action=action,
    )
    if not has_permission and others:
        for alt in others:
            has_permission = await role_service.check_user_permission(
                user_id=current_user["id"],
                permission_name=alt["name"],
                resource=alt["resource"],
                action=alt["action"],
            )
            if has_permission:
                break

    if not has_permission:
        raise HTTPException(
            status_code=403,
            detail=response_message(
                error="Insufficient permissions",
                success_status=False,
                message=f"Permission '{permission_name}' required",
            ),
        )
    return True
