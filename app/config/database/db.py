# app/config/database/db.py
import contextlib
from datetime import datetime, timedelta, timezone
from typing import AsyncIterator, Optional

from sqlalchemy import DateTime, ForeignKey, String, event
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config.database.optimized_pool import get_optimized_pool_config, optimized_pool
from app.utils.database.query_analyzer import setup_database_monitoring
from app.utils.logger.log import logs
from app.utils.uuid_generator import id_gen


class Base(DeclarativeBase):
    pass


class TimeStamp:
    GMT_PLUS_1 = timezone(timedelta(hours=1))

    @staticmethod
    def _get_current_time():
        return datetime.now(TimeStamp.GMT_PLUS_1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(TimeStamp.GMT_PLUS_1),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(TimeStamp.GMT_PLUS_1), onupdate=lambda: datetime.now(TimeStamp.GMT_PLUS_1)
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditFields:
    """Audit fields for tracking who created and updated records"""

    created_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("USER.id", ondelete="CASCADE"), nullable=True, default=None
    )
    updated_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("USER.id", ondelete="CASCADE"), nullable=True, default=None
    )


class BaseModelClass(Base, TimeStamp, AuditFields):
    __abstract__ = True

    @declared_attr
    def id(cls) -> Mapped[str]:
        return mapped_column(String(255), primary_key=True, default=id_gen, unique=True)

    @classmethod
    def __declare_last__(cls):
        @event.listens_for(cls, "before_insert")
        def receive_before_insert(mapper, connection, instance):
            if instance.id is None:
                instance.id = id_gen()


class DatabaseSessionManager:
    def __init__(self):
        self._engine: AsyncEngine | None = None
        self._sessionmaker: async_sessionmaker | None = None

    def init(
        self,
        host: str,
        pool_size: int = 20,
        max_overflow: int = 40,
        echo: bool = False,
        use_optimized: bool = True,
    ):
        if host.startswith("postgres://"):
            host = host.replace("postgres://", "postgresql+asyncpg://", 1)
        elif host.startswith("postgresql://") and not host.startswith("postgresql+"):
            host = host.replace("postgresql://", "postgresql+asyncpg://", 1)

        if use_optimized:
            # Use optimized pool configuration
            optimized_config = get_optimized_pool_config()
            optimized_config.update({"echo": echo})

            logs.info(
                "🔧 [DB] Using optimized pool configuration with NullPool for async compatibility"
            )
            self._engine = optimized_pool.create_optimized_engine(
                host, **optimized_config
            )

            # Setup query monitoring for performance analysis
            setup_database_monitoring(self._engine.sync_engine)
        else:
            # Use standard configuration
            self._engine = create_async_engine(
                host,
                echo=echo,  # Enable SQL query logging when True
                pool_pre_ping=True,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=3600,  # Recycle connections after 1 hour
                pool_timeout=30,  # Wait 30s for connection from pool
                query_cache_size=500,  # Cache compiled queries
            )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine, expire_on_commit=False, autoflush=False, autocommit=False
        )

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_all(self, connection: AsyncConnection):
        try:
            await connection.run_sync(Base.metadata.create_all)
        except Exception as e:
            # Handle database conflicts gracefully
            if any(
                keyword in str(e).lower()
                for keyword in ["already exists", "duplicate", "relation"]
            ):
                logs.warning(f"Database object already exists, continuing: {e}")
            else:
                raise e

    async def drop_all(self, connection: AsyncConnection):
        logs.info("Dropping all tables")
        await connection.run_sync(Base.metadata.drop_all)


session_manager = DatabaseSessionManager()


async def get_db() -> AsyncIterator[AsyncSession]:
    async with session_manager.session() as session:
        yield session


# import contextlib
# from datetime import datetime
# from typing import AsyncIterator, Literal

# from fastapi import Depends
# from sqlalchemy import create_engine, func
# from sqlalchemy.engine import Engine
# from sqlalchemy.ext.asyncio import (AsyncConnection, AsyncEngine, AsyncSession,
#                                     async_sessionmaker, create_async_engine)
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import (DeclarativeBase, Mapped, Session, declarative_base,
#                             mapped_column, relationship, sessionmaker)

# from app.config import env
# from app.utils.logger import log

# # SQLALCHEMY_DATABASE_URL: Literal["sqlite:///./flow.db"] = "sqlite:///./flow.db"

# # engine: Engine = create_engine(
# #     SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
# # )

# engine: Engine = create_engine(env.env['database_url'])
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # Base = declarative_base(

# class Base(DeclarativeBase):
#     pass

# class DatabaseSessionManager:
#     def __init__(self):
#         self._engine: AsyncEngine | None = None
#         self._sessionmaker: async_sessionmaker | None = None

#     def init(self, host: str):
#         self._engine = create_async_engine(
#             host,
#             echo=False,  # Set to True for SQL query logging
#             pool_pre_ping=True,  # Enable connection pool pre-ping
#             pool_size=10,  # Maximum number of connections in the pool
#             max_overflow=20  # Maximum number of connections that can be created beyond pool_size
#         )
#         self._sessionmaker = async_sessionmaker(
#             bind=self._engine,
#             expire_on_commit=False,
#             autoflush=False,
#             autocommit=False
#         )

#     async def close(self):
#         if self._engine is None:
#             raise Exception("DatabaseSessionManager is not initialized")
#         await self._engine.dispose()
#         self._engine = None
#         self._sessionmaker = None

#     @contextlib.asynccontextmanager
#     async def connect(self) -> AsyncIterator[AsyncConnection]:
#         if self._engine is None:
#             raise Exception("DatabaseSessionManager is not initialized")

#         async with self._engine.begin() as connection:
#             try:
#                 yield connection
#             except Exception:
#                 await connection.rollback()
#                 raise
#             finally:
#                 await connection.close()

#     @contextlib.asynccontextmanager
#     async def session(self) -> AsyncIterator[AsyncSession]:
#         if self._sessionmaker is None:
#             raise Exception("DatabaseSessionManager is not initialized")

#         async with self._sessionmaker() as session:
#             try:
#                 yield session
#             except Exception:
#                 await session.rollback()
#                 raise
#             finally:
#                 await session.close()

#     # Used for testing
#     async def create_all(self, connection: AsyncConnection):
#         await connection.run_sync(Base.metadata.create_all)

#     async def drop_all(self, connection: AsyncConnection):
#         await connection.run_sync(Base.metadata.drop_all)


# session_manager = DatabaseSessionManager()
# async def get_db():
#     async with session_manager.session() as session:
#        yield session


# class TimeStamp(object):
#     created_at: Mapped[datetime] = mapped_column(default=func.now())
#     updated_at: Mapped[datetime] = mapped_column(default=func.now())
