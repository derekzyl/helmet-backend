from typing import Any, Optional

from fastapi import Request
from fastapi.security import HTTPBearer
from sqlalchemy.future import select as sa_select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config.database.db import DatabaseSessionManager
from app.core.auth.services.service_token import TokenService
from app.core.users.models.model_user import UserModel
from app.utils.convert_sqlalchemy_dict import sqlalchemy_obj_to_dict
from app.utils.crud.types_crud import ResponseMessage, response_message
from app.utils.logger import log

security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_session: DatabaseSessionManager):
        super().__init__(app)
        self.db = db_session
        self.token_service = TokenService

    async def get_current_user(self, token: str) -> Optional[ResponseMessage]:
        try:
            token_result: str = await self.token_service.verify_jwt_token(token=token)
            if not token_result:
                return ResponseMessage(
                    data=None,
                    doc_length=0,
                    error="Invalid or expired token",
                    message="Unauthorized",
                    success_status=False,
                )

            user_service = UserServices(self.db)
            user = await user_service.get_one({"id": token_result})
            if not user or not user.get("data"):
                return ResponseMessage(
                    data=None,
                    doc_length=0,
                    error="User not found",
                    message="Unauthorized",
                    success_status=False,
                )
            return user
        except Exception as e:
            log.logs.error(f"Error getting user: {e}")
            return None

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.method == "OPTIONS":
            return await call_next(request)

        if self.should_skip_auth(request.url.path):
            return await call_next(request)

        try:
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=401,
                    content=response_message(
                        error="Missing authorization header",
                        success_status=False,
                        message="Unauthorized",
                    ),
                )

            try:
                scheme, token = auth_header.split(" ", 1)
                if scheme.lower() != "bearer":
                    from fastapi.responses import JSONResponse

                    return JSONResponse(
                        status_code=401,
                        content=response_message(
                            error="Invalid authentication scheme",
                            success_status=False,
                            message="Unauthorized",
                        ),
                    )
            except ValueError:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=401,
                    content=response_message(
                        error="Invalid authorization header format",
                        success_status=False,
                        message="Unauthorized",
                    ),
                )

            current_user_response = await self.get_current_user(token)
            if not current_user_response or "data" not in current_user_response:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=401,
                    content=response_message(
                        error="Invalid or expired token",
                        success_status=False,
                        message="Unauthorized",
                    ),
                )

            user_payload = current_user_response.get("data")
            if user_payload is None:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=401,
                    content=response_message(
                        error="Invalid user payload",
                        success_status=False,
                        message="Unauthorized",
                    ),
                )

            udict = (
                user_payload
                if isinstance(user_payload, dict)
                else sqlalchemy_obj_to_dict(user_payload)
            )
            if isinstance(udict, dict) and udict.get("allow_login") is False:
                from fastapi.responses import JSONResponse

                return JSONResponse(
                    status_code=401,
                    content=response_message(
                        error="Account disabled",
                        success_status=False,
                        message="Unauthorized",
                    ),
                )

            request.state.user = user_payload
            return await call_next(request)

        except Exception as e:
            log.logs.error(f"Authentication error: {str(e)}")
            from fastapi.responses import JSONResponse

            return JSONResponse(
                status_code=401,
                content=response_message(
                    error=str(e), success_status=False, message="Authentication failed"
                ),
            )

    def should_skip_auth(self, path: str) -> bool:
        exact_paths = {
            "/",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/verify-email",
            "/api/v1/auth/refresh-token",
            "/api/v1/auth/register",
            "/api/v1/auth/send-verification-email",
            "/api/v1/auth/health",
            "/api/v1/system/health",
            "/api/v1/social/google",
            "/api/v1/social/facebook",
            "/api/v1/social/github",
        }
        prefix_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/v1/social",
            "/api/v1/devices",
            "/api/v1/telemetry",
            "/api/v1/events",
            "/api/v1/contacts",
            "/api/v1/ws",
        }
        if path in exact_paths:
            return True
        return any(path.startswith(prefix) for prefix in prefix_paths)


class UserServices:
    def __init__(self, db: DatabaseSessionManager):
        self.db = db
        self.model = UserModel

    async def get_one(
        self, data: dict[str, Any], select: Optional[list[str]] = None
    ) -> ResponseMessage:
        async with self.db.session() as session:
            try:
                query = sa_select(self.model).filter_by(**data)
                if select:
                    include_fields = [
                        field for field in select if not field.startswith("-")
                    ]
                    exclude_fields = [
                        field[1:] for field in select if field.startswith("-")
                    ]
                    if include_fields:
                        fields_to_select = [
                            getattr(self.model, field) for field in include_fields
                        ]
                        query = sa_select(*fields_to_select).filter_by(**data)
                    else:
                        all_fields = set(self.model.__table__.columns.keys())
                        fields_to_select = [
                            getattr(self.model, field)
                            for field in all_fields
                            if field not in exclude_fields
                        ]
                        query = sa_select(*fields_to_select).filter_by(**data)

                result = await session.execute(query)
                db_item_selected = result.scalar()
                result_dict = sqlalchemy_obj_to_dict(db_item_selected)
                if isinstance(result_dict, dict) and "password" in result_dict:
                    del result_dict["password"]

                return response_message(
                    data=result_dict,
                    doc_length=1,
                    error=None,
                    message="Data fetched successfully",
                    success_status=True,
                )
            except Exception as e:
                log.logs.error(f"Error executing query: {e}")
                return response_message(
                    data=None,
                    doc_length=0,
                    error=str(e),
                    message="Error fetching data",
                    success_status=False,
                )
