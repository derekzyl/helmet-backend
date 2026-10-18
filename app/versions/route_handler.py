from typing import Any, Dict

from fastapi import FastAPI

from .v1 import routesV1


def handle_routing(app: FastAPI):
    """Register all v1 routes with access-level tags for OpenAPI docs."""
    default_responses: Dict[int | str, Dict[str, Any]] = {
        200: {"description": "Success"},
        201: {"description": "Created"},
        204: {"description": "No Content"},
        400: {"description": "Bad Request"},
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        404: {"description": "Not Found"},
        500: {"description": "Internal Server Error"},
    }

    for route in routesV1:
        enhanced_tags = [
            f"{tag} ({route['access_level'].value.upper()})" for tag in route["tags"]
        ]
        app.include_router(
            router=route["api_route"],
            prefix=f"/api/v1/{route['path']}",
            tags=enhanced_tags,
            responses=route.get("responses", default_responses),
        )
