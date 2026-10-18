from fastapi import APIRouter
from fastapi.responses import JSONResponse

health_router = APIRouter()


@health_router.get("/health")
async def health_check():
    """Basic health check for load balancers and uptime monitors."""
    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "message": "OK",
            "data": {"status": "healthy", "service": "fastapi-sqlalchemy-starter"},
        },
    )
