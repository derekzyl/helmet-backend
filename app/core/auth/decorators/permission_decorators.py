from functools import wraps
from typing import Callable, Optional

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.services.middleware_auth import response_message
from app.core.auth.services.service_auth import OthersTypes, check_permission


def require_permission(
    permission_name: str,
    resource: str,
    action: str,
    others: Optional[list[OthersTypes]] = None,
):
    """Decorator to require a specific permission for route access."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            db = kwargs.get("db")

            for arg in args:
                if isinstance(arg, dict) and "id" in arg and "email" in arg:
                    current_user = arg
                elif isinstance(arg, AsyncSession):
                    db = arg

            if not current_user or not db:
                raise HTTPException(
                    status_code=401,
                    detail=response_message(
                        error="User not authenticated",
                        success_status=False,
                        message="Authentication required",
                    ),
                )

            await check_permission(
                permission_name=permission_name,
                resource=resource,
                action=action,
                current_user=current_user,
                db=db,
                others=others,
            )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(permissions: list[OthersTypes]):
    """Require at least one of the listed permissions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            db = kwargs.get("db")

            for arg in args:
                if isinstance(arg, dict) and "id" in arg and "email" in arg:
                    current_user = arg
                elif isinstance(arg, AsyncSession):
                    db = arg

            if not current_user or not db or not permissions:
                raise HTTPException(
                    status_code=401,
                    detail=response_message(
                        error="User not authenticated",
                        success_status=False,
                        message="Authentication required",
                    ),
                )

            first, *rest = permissions
            await check_permission(
                permission_name=first["name"],
                resource=first["resource"],
                action=first["action"],
                current_user=current_user,
                db=db,
                others=rest or None,
            )
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(permissions: list[OthersTypes]):
    """Require all of the listed permissions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            db = kwargs.get("db")

            for arg in args:
                if isinstance(arg, dict) and "id" in arg and "email" in arg:
                    current_user = arg
                elif isinstance(arg, AsyncSession):
                    db = arg

            if not current_user or not db:
                raise HTTPException(
                    status_code=401,
                    detail=response_message(
                        error="User not authenticated",
                        success_status=False,
                        message="Authentication required",
                    ),
                )

            for permission in permissions:
                await check_permission(
                    permission_name=permission["name"],
                    resource=permission["resource"],
                    action=permission["action"],
                    current_user=current_user,
                    db=db,
                )
            return await func(*args, **kwargs)

        return wrapper

    return decorator
