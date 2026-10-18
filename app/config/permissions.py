platform_permissions = {
    "platform": {
        "manage": {
            "name": "platform_admin",
            "resource": "platform",
            "action": "manage",
            "description": "Full platform administration access",
            "permission_level": "platform",
        },
        "analytics": {
            "name": "platform_analytics",
            "resource": "platform",
            "action": "analytics",
            "description": "View platform-wide analytics",
            "permission_level": "platform",
        },
    },
    "users": {
        "manage": {
            "name": "user_management",
            "resource": "users",
            "action": "manage",
            "description": "Manage system users and accounts",
            "permission_level": "platform",
        },
        "read": {
            "name": "user_read",
            "resource": "users",
            "action": "read",
            "description": "View user accounts",
            "permission_level": "platform",
        },
    },
    "system": {
        "configure": {
            "name": "system_settings",
            "resource": "system",
            "action": "configure",
            "description": "Configure system-wide settings",
            "permission_level": "platform",
        },
    },
    "roles": {
        "manage": {
            "name": "role_management",
            "resource": "roles",
            "action": "manage",
            "description": "Manage roles and permissions",
            "permission_level": "platform",
        },
    },
    "files": {
        "upload": {
            "name": "file_upload",
            "resource": "files",
            "action": "upload",
            "description": "Upload files",
            "permission_level": "user",
        },
    },
}

user_permissions = {
    "profile": {
        "read": {
            "name": "profile_read",
            "resource": "profile",
            "action": "read",
            "description": "View own profile",
            "permission_level": "user",
        },
        "update": {
            "name": "profile_update",
            "resource": "profile",
            "action": "update",
            "description": "Update own profile",
            "permission_level": "user",
        },
    },
}


def flatten_permissions(*catalogs: dict) -> list[dict]:
    """Flatten nested permission catalogs into a list of permission dicts."""
    result: list[dict] = []
    for catalog in catalogs:
        for resource_group in catalog.values():
            for permission in resource_group.values():
                result.append(permission)
    return result


ALL_PERMISSIONS = flatten_permissions(platform_permissions, user_permissions)
