from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from app.config.database.db import session_manager
from app.config.env import env
from app.core.auth.services.optimized_middleware_auth import HybridAuthMiddleware
from app.middleware.performance_middleware import PerformanceMiddleware
from app.utils.cache.redis_cache import cache_manager
from app.utils.logger.log import logs
from app.versions.route_handler import handle_routing


def init_app(init_db=True):
    app: FastAPI = FastAPI(
        title="Smart Helmet",
        description="A clean FastAPI + async SQLAlchemy starter with auth, users, and RBAC scaffolding.",
        version="0.1.0",
        default_response_class=ORJSONResponse,
    )

    origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "https://helmet-dashboard-nine.vercel.app",
    ]
    allow_origin_regex = r"http(s)?://(localhost|127\.0\.0\.1)(:\d+)?"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Accept",
            "Accept-Language",
            "Content-Language",
            "Content-Type",
            "Authorization",
            "X-Requested-With",
        ],
        expose_headers=["*"],
        max_age=600,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(PerformanceMiddleware)
    app.add_middleware(
        HybridAuthMiddleware, db_session=session_manager, use_optimized=True
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            if init_db:
                pool_size = env.get("performance", {}).get("db_pool_size", 20)
                max_overflow = env.get("performance", {}).get("db_max_overflow", 40)
                enable_query_logging = env.get("performance", {}).get(
                    "enable_query_logging", False
                )

                logs.info(
                    f"Initializing database with pool_size={pool_size}, "
                    f"max_overflow={max_overflow}, query_logging={enable_query_logging}"
                )
                session_manager.init(
                    env["database_url"],
                    pool_size=pool_size,
                    max_overflow=max_overflow,
                    echo=enable_query_logging,
                    use_optimized=True,
                )

                redis_url = env.get("performance", {}).get(
                    "redis_url", "redis://localhost:6379"
                )
                cache_enabled = env.get("performance", {}).get("cache_enabled", True)

                try:
                    await cache_manager.init(redis_url, enabled=cache_enabled)
                    if cache_manager.enabled:
                        logs.info("Redis cache initialized successfully")
                    else:
                        logs.warning("Caching is disabled or Redis not available")
                except Exception as e:
                    logs.error(f"Failed to initialize Redis cache: {e}")
                    logs.warning("Continuing without caching...")

                async with session_manager.connect() as connection:
                    await session_manager.create_all(connection)

            yield
        finally:
            if session_manager._engine is not None:
                await session_manager.close()

            if cache_manager.redis is not None:
                await cache_manager.close()

    app.router.lifespan_context = lifespan  # pyright: ignore[reportAttributeAccessIssue]
    handle_routing(app=app)

    from app.core.telemetry.routes.routes_telemetry import telemetry_websocket_endpoint

    app.add_api_websocket_route("/api/v1/ws/live", telemetry_websocket_endpoint)

    return app
