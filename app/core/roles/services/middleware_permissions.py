import re
from typing import Dict, Optional, Tuple

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.database.db import get_db
from app.core.users.services.service_user import UserService
from app.utils.crud.types_crud import response_message


class PermissionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically check permissions based on route patterns
    """

    def __init__(self, app, route_permissions: Dict[str, Tuple[str, str, str]]|None = None):
        """
        Initialize permission middleware

        Args:
            app: FastAPI application
            route_permissions: Dictionary mapping route patterns to (permission, resource, action)
                              Format: {"/api/users/*": ("manage_users", "users", "read")}
        """
        super().__init__(app)
        self.route_permissions = route_permissions or {}

        # Default route patterns - you can customize these
        self.default_patterns = {
            # Admin routes
            r"/api/admin/.*": ("admin_access", "system", "manage"),
            # User management routes
            r"/api/users$": {
                "GET": ("view_users", "users", "read"),
                "POST": ("create_user", "users", "create"),
            },
            r"/api/users/[^/]+$": {
                "GET": ("view_user", "users", "read"),
                "PUT": ("edit_user", "users", "update"),
                "PATCH": ("edit_user", "users", "update"),
                "DELETE": ("delete_user", "users", "delete"),
            },
            # Generic patterns
            r"/api/([^/]+)$": {
                "GET": ("view_{resource}", "{resource}", "read"),
                "POST": ("create_{resource}", "{resource}", "create"),
            },
            r"/api/([^/]+)/[^/]+$": {
                "GET": ("view_{resource}", "{resource}", "read"),
                "PUT": ("edit_{resource}", "{resource}", "update"),
                "PATCH": ("edit_{resource}", "{resource}", "update"),
                "DELETE": ("delete_{resource}", "{resource}", "delete"),
            },
        }

    async def dispatch(self, request: Request, call_next):
        """Process request and check permissions if needed"""

        # Skip permission check for certain paths
        if self._should_skip_permission_check(request):
            return await call_next(request)

        # Check if route requires permission check
        permission_requirement = self._get_permission_requirement(request)

        if permission_requirement:
            try:
                await self._check_permission(request, permission_requirement)
            except HTTPException as e:
                # Return error response
                from fastapi.responses import JSONResponse

                return JSONResponse(status_code=e.status_code, content=e.detail)

        # Continue with request
        response = await call_next(request)
        return response

    def _should_skip_permission_check(self, request: Request) -> bool:
        """Check if permission check should be skipped for this route"""
        skip_paths = [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/api/health",
        ]

        path = request.url.path
        method = request.method

        # Skip for specific paths
        if any(path.startswith(skip_path) for skip_path in skip_paths):
            return True

        # Skip for OPTIONS requests
        if method == "OPTIONS":
            return True

        return False

    def _get_permission_requirement(
        self, request: Request
    ) -> Optional[Tuple[str, str, str]]:
        """Get permission requirement for the current route"""
        path = request.url.path
        method = request.method

        # Check explicit route permissions first
        for pattern, requirement in self.route_permissions.items():
            if re.match(pattern, path):
                return requirement

        # Check default patterns
        for pattern, requirement in self.default_patterns.items():
            match = re.match(pattern, path)
            if match:
                if isinstance(requirement, dict):
                    # Method-specific requirements
                    if method in requirement:
                        req = requirement[method]
                        return self._process_requirement_template(req, match, path)
                else:
                    # Single requirement for all methods
                    return self._process_requirement_template(requirement, match, path)

        return None

    def _process_requirement_template(
        self, requirement: Tuple[str, str, str], match: re.Match, path: str
    ) -> Tuple[str, str, str]:
        """Process requirement template with captured groups"""
        permission, resource, action = requirement

        # Replace placeholders with captured groups
        if match.groups():
            # Extract resource name from path (e.g., "users" from "/api/users")
            resource_name = match.group(1) if len(match.groups()) >= 1 else "resource"

            permission = permission.replace("{resource}", resource_name)
            resource = resource.replace("{resource}", resource_name)

        return (permission, resource, action)

    async def _check_permission(
        self, request: Request, requirement: Tuple[str, str, str]
    ):
        """Check if user has required permission"""
        permission_name, resource, action = requirement

        # Get user from request state (should be set by authentication middleware)
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

        # Get database session
        db_gen = get_db()
        db = await db_gen.__anext__()

        try:
            # Create user service and check permission
            user_service = UserService(db)
            has_permission = await user_service.check_user_permission(
                user_id=user.id,
                required_permission=permission_name,
                resource=resource,
                action=action,
            )

            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=response_message(
                        error="Insufficient permissions",
                        success_status=False,
                        message=f"Permission '{permission_name}' required for resource '{resource}' and action '{action}'",
                    ),
                )

        finally:
            await db.close()


# Configuration helper
class PermissionConfig:
    """Helper class to configure permission middleware"""

    @staticmethod
    def create_route_permissions() -> Dict[str, Tuple[str, str, str]]:
        """Create route permission mappings"""
        return {
            # Exact matches
            "/api/admin/dashboard": ("admin_dashboard", "admin", "read"),
            "/api/admin/users": ("admin_manage_users", "admin", "manage"),
            "/api/admin/settings": ("admin_settings", "admin", "manage"),
            # User profile routes
            "/api/profile": ("view_profile", "profile", "read"),
            "/api/profile/update": ("edit_profile", "profile", "update"),
            # Specific resource routes
            "/api/reports/.*": ("view_reports", "reports", "read"),
            "/api/analytics/.*": ("view_analytics", "analytics", "read"),
            # File management
            "/api/files/upload": ("upload_files", "files", "create"),
            "/api/files/download/.*": ("download_files", "files", "read"),
            "/api/files/delete/.*": ("delete_files", "files", "delete"),
        }

    @staticmethod
    def setup_middleware(app, custom_routes: dict[str, tuple[str, str, str]]|None = None):
        """Setup permission middleware on FastAPI app"""
        route_permissions = PermissionConfig.create_route_permissions()

        if custom_routes:
            route_permissions.update(custom_routes)

        app.add_middleware(PermissionMiddleware, route_permissions=route_permissions)


# Example usage:
"""
from fastapi import FastAPI
from app.middleware.permission_middleware import PermissionConfig

app = FastAPI()

# Setup permission middleware with default configuration
PermissionConfig.setup_middleware(app)

# Or with custom routes
custom_routes = {
    "/api/special/action": ("special_permission", "special", "execute"),
    "/api/custom/.*": ("custom_access", "custom", "read")
}
PermissionConfig.setup_middleware(app, custom_routes)
"""
