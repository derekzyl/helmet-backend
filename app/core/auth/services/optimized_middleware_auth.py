# optimized_middleware/auth.py
import hashlib
import json
from typing import Any, Optional

from fastapi import Request
from fastapi.security import HTTPBearer
from sqlalchemy.future import select as sa_select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.config.database.db import DatabaseSessionManager
from app.core.auth.services.service_token import TokenService
from app.core.users.models.model_user import UserModel
from app.utils.cache.redis_cache import cache_manager
from app.utils.convert_sqlalchemy_dict import sqlalchemy_obj_to_dict
from app.utils.crud.types_crud import ResponseMessage, response_message
from app.utils.logger import log

security = HTTPBearer()


class OptimizedAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, db_session: DatabaseSessionManager):
        super().__init__(app)
        self.db = db_session
        self.token_service = TokenService
        self.user_cache_ttl = 300  # 5 minutes cache for user data
        self.token_cache_ttl = 60  # 1 minute cache for token validation

    async def get_current_user(self, token: str) -> Optional[ResponseMessage]:
        try:
            # Generate cache key for token validation
            token_hash = hashlib.md5(token.encode()).hexdigest()
            token_cache_key = f"auth_token:{token_hash}"
            user_cache_key = f"auth_user:{token_hash}"

            # Check token cache first
            cached_token_result = await cache_manager.get(token_cache_key)
            if cached_token_result:
                log.logs.debug("Token cache hit for user lookup")
                # Get user from cache
                cached_user = await cache_manager.get(user_cache_key)
                if cached_user:
                    return ResponseMessage(
                        data=cached_user,
                        doc_length=1,
                        error=None,
                        message="Data fetched successfully",
                        success_status=True,
                    )

            # Verify token
            token_result: str = await self.token_service.verify_jwt_token(token=token)

            if not token_result:
                return ResponseMessage(
                    data=None,
                    doc_length=0,
                    error="Invalid or expired token",
                    message="Unauthorized",
                    success_status=False,
                )

            # Cache token validation result
            await cache_manager.set(
                token_cache_key, token_result, expire=self.token_cache_ttl
            )

            # Get user with optimized service
            user_service = OptimizedUserServices(self.db)
            user = await user_service.get_one({"id": token_result})

            if not user or not user.get("data"):
                return ResponseMessage(
                    data=None,
                    doc_length=0,
                    error="User not found",
                    message="Unauthorized",
                    success_status=False,
                )

            # Cache user data
            user_data = user.get("data")
            await cache_manager.set(
                user_cache_key, user_data, expire=self.user_cache_ttl
            )

            return user
        except Exception as e:
            log.logs.error(f"Error getting user: {e}")
            return None

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # CRITICAL FIX: Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Skip authentication for public paths
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

            # Handle Bearer token format
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

            # Authenticate user with caching
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

            # Pass to the next middleware or route handler
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
        """Define paths that should skip authentication"""
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

        return any(path.startswith(prefix_path) for prefix_path in prefix_paths)


class OptimizedUserServices:
    def __init__(self, db: DatabaseSessionManager):
        self.db = db
        self.model = UserModel
        self.cache_ttl = 300  # 5 minutes

    async def get_one(
        self, data: dict[str, Any], select: Optional[list[str]] = None
    ) -> ResponseMessage:
        # Generate cache key
        cache_key = f"user_data:{hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()}"

        # Check cache first
        cached_result = await cache_manager.get(cache_key)
        if cached_result:
            # log.logs.debug(f"User cache hit for {data}")
            return ResponseMessage(
                data=cached_result,
                doc_length=1,
                error=None,
                message="Data fetched successfully",
                success_status=True,
            )

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

                # Execute the query with AsyncSession
                result = await session.execute(query)
                db_item_selected = result.scalar()

                # Convert to dict for JSON serialization
                result_dict = sqlalchemy_obj_to_dict(db_item_selected)
                if isinstance(result_dict, dict) and "password" in result_dict:
                    del result_dict["password"]

                # Cache the result
                await cache_manager.set(cache_key, result_dict, expire=self.cache_ttl)

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


# Hybrid middleware that can use either optimized or original implementation
class HybridAuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app, db_session: DatabaseSessionManager, use_optimized: bool = True
    ):
        super().__init__(app)
        self.db = db_session
        self.use_optimized = use_optimized

        # Initialize both middlewares
        self.optimized_middleware = OptimizedAuthMiddleware(app, db_session)
        from app.core.auth.services.middleware_auth import AuthMiddleware

        self.original_middleware = AuthMiddleware(app, db_session)

        # Performance tracking
        self.optimized_calls = 0
        self.original_calls = 0
        self.cache_hits = 0

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self.use_optimized:
            self.optimized_calls += 1
            return await self.optimized_middleware.dispatch(request, call_next)
        else:
            self.original_calls += 1
            return await self.original_middleware.dispatch(request, call_next)

    def get_performance_stats(self) -> dict:
        total_calls = self.optimized_calls + self.original_calls
        return {
            "optimized_calls": self.optimized_calls,
            "original_calls": self.original_calls,
            "total_calls": total_calls,
            "optimized_usage_percentage": (self.optimized_calls / total_calls * 100)
            if total_calls > 0
            else 0,
        }

    def switch_to_optimized(self):
        self.use_optimized = True
        log.logs.info("Switched to optimized auth middleware")

    def switch_to_original(self):
        self.use_optimized = False
        log.logs.info("Switched to original auth middleware")


# Import the original middleware for hybrid functionality
