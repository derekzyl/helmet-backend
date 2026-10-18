"""
API Version 1 (v1)
-----------------
Starter routers: auth, social auth, users, admin, system settings, file upload, health.
"""

from app.core.admin.routes.performance_routes import router as performance_router
from app.core.admin.routes.platform_staff import platform_staff_router
from app.core.auth.routes.auth_route import auth_router
from app.core.auth.routes.social_route import social_auth_router
from app.core.contacts.routes.routes_contacts import contact_router
from app.core.devices.routes.routes_devices import device_router
from app.core.events.routes.routes_events import event_router
from app.core.system.routes.file_upload_route import file_upload_router
from app.core.system.routes.health_route import health_router
from app.core.system.routes.system_setting_route import system_setting_router
from app.core.telemetry.routes.routes_telemetry import telemetry_router
from app.core.users.routes.routes_users import user_router
from app.versions.types_routes import AccessLevel, RouterData

routesV1: list[RouterData] = [
    {
        "api_route": health_router,
        "path": "system",
        "tags": ["Health"],
        "access_level": AccessLevel.PUBLIC,
        "description": "Health and readiness checks.",
    },
    {
        "api_route": auth_router,
        "path": "auth",
        "tags": ["Authentication"],
        "access_level": AccessLevel.PUBLIC,
        "description": "Login, register, password reset, and token management.",
    },
    {
        "api_route": social_auth_router,
        "path": "social",
        "tags": ["Social Authentication"],
        "access_level": AccessLevel.PUBLIC,
        "description": "Google, Facebook, and GitHub OAuth integration.",
    },
    {
        "api_route": user_router,
        "path": "user",
        "tags": ["User Management"],
        "access_level": AccessLevel.ADMIN,
        "description": "User account management.",
    },
    {
        "api_route": platform_staff_router,
        "path": "admin/platform-staff",
        "tags": ["Platform Staff Management"],
        "access_level": AccessLevel.ADMIN,
        "description": "Platform-level staff, roles, and permissions.",
    },
    {
        "api_route": performance_router,
        "path": "admin/performance",
        "tags": ["Performance Monitoring"],
        "access_level": AccessLevel.ADMIN,
        "description": "Database and API performance monitoring.",
    },
    {
        "api_route": system_setting_router,
        "path": "system-setting",
        "tags": ["System Settings"],
        "access_level": AccessLevel.ADMIN,
        "description": "System configuration and settings.",
    },
    {
        "api_route": file_upload_router,
        "path": "file-upload",
        "tags": ["File Upload"],
        "access_level": AccessLevel.AUTHENTICATED,
        "description": "File upload and management.",
    },
    {
        "api_route": device_router,
        "path": "devices",
        "tags": ["Devices"],
        "access_level": AccessLevel.PUBLIC,
        "description": "Smart Helmet and Bike Ignition device registry and pairing.",
    },
    {
        "api_route": telemetry_router,
        "path": "telemetry",
        "tags": ["Telemetry"],
        "access_level": AccessLevel.PUBLIC,
        "description": "Live and historical telemetry ingest and query.",
    },
    {
        "api_route": event_router,
        "path": "events",
        "tags": ["Safety Events"],
        "access_level": AccessLevel.PUBLIC,
        "description": "Incident alerts, collision logs, and alarm acknowledgement.",
    },
    {
        "api_route": contact_router,
        "path": "contacts",
        "tags": ["Emergency Contacts"],
        "access_level": AccessLevel.PUBLIC,
        "description": "Emergency contacts management for SMS/call dispatch.",
    },
]
