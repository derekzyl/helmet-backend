"""
Optimized database connection pool for 2 vCPU + 8GB RAM server
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import QueuePool

from app.config.server import DATABASE_POOL_CONFIG

logger = logging.getLogger(__name__)

class OptimizedConnectionPool:
    """
    Optimized connection pool for 2 vCPU + 8GB RAM server
    """
    
    def __init__(self):
        self.engine: Optional[Engine] = None
        self.async_engine = None
        self.async_session_factory = None
        self._connection_count = 0
        self._max_connections = DATABASE_POOL_CONFIG["pool_size"] + DATABASE_POOL_CONFIG["max_overflow"]
        
    def initialize(self, database_url: str):
        """
        Initialize the connection pool
        """
        try:
            # Create synchronous engine with optimized pool
            self.engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=DATABASE_POOL_CONFIG["pool_size"],
                max_overflow=DATABASE_POOL_CONFIG["max_overflow"],
                pool_timeout=DATABASE_POOL_CONFIG["pool_timeout"],
                pool_recycle=DATABASE_POOL_CONFIG["pool_recycle"],
                pool_pre_ping=DATABASE_POOL_CONFIG["pool_pre_ping"],
                echo=False,  # Disable SQL logging in production
                connect_args={
                    "options": "-c default_transaction_isolation=read_committed"
                }
            )
            
            # Create asynchronous engine
            async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
            self.async_engine = create_async_engine(
                async_url,
                pool_size=DATABASE_POOL_CONFIG["pool_size"],
                max_overflow=DATABASE_POOL_CONFIG["max_overflow"],
                pool_timeout=DATABASE_POOL_CONFIG["pool_timeout"],
                pool_recycle=DATABASE_POOL_CONFIG["pool_recycle"],
                pool_pre_ping=DATABASE_POOL_CONFIG["pool_pre_ping"],
                echo=False,
                connect_args={
                    "server_settings": {
                        "application_name": "fastapi_starter",
                        "jit": "off",  # Disable JIT for better performance
                    }
                }
            )
            
            # Create async session factory
            self.async_session_factory = async_sessionmaker(
                self.async_engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Add connection event listeners
            self._setup_connection_listeners()
            
            logger.info(f"Database connection pool initialized with {DATABASE_POOL_CONFIG['pool_size']} base connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    def _setup_connection_listeners(self):
        """
        Setup connection event listeners for monitoring
        """
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """
            Set connection-specific parameters
            """
            with dbapi_connection.cursor() as cursor:
                # Optimize PostgreSQL connection
                cursor.execute("SET default_transaction_isolation TO 'read committed'")
                cursor.execute("SET statement_timeout TO '30s'")
                cursor.execute("SET lock_timeout TO '10s'")
                cursor.execute("SET idle_in_transaction_session_timeout TO '60s'")
        
        @event.listens_for(self.engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """
            Monitor connection checkout
            """
            self._connection_count += 1
            if self._connection_count > self._max_connections * 0.8:
                logger.warning(f"High connection usage: {self._connection_count}/{self._max_connections}")
        
        @event.listens_for(self.engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """
            Monitor connection checkin
            """
            self._connection_count -= 1
    
    @asynccontextmanager
    async def get_async_session(self):
        """
        Get async database session with automatic cleanup
        """
        if not self.async_session_factory:
            raise RuntimeError("Async session factory not initialized")
        
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
    
    def get_sync_session(self):
        """
        Get synchronous database session
        """
        from sqlalchemy.orm import sessionmaker
        Session = sessionmaker(bind=self.engine)
        return Session()
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get connection pool statistics
        """
        if not self.engine:
            return {}
        
        pool = self.engine.pool
        return {
            "pool_size": getattr(pool, 'size', lambda: 0)(),
            "checked_in": getattr(pool, 'checkedin', lambda: 0)(),
            "checked_out": getattr(pool, 'checkedout', lambda: 0)(),
            "overflow": getattr(pool, 'overflow', lambda: 0)(),
            "invalid": getattr(pool, 'invalid', lambda: 0)(),
            "current_connections": self._connection_count,
            "max_connections": self._max_connections,
            "utilization_percent": (self._connection_count / self._max_connections) * 100
        }
    
    def health_check(self) -> bool:
        """
        Perform health check on the connection pool
        """
        try:
            if not self.engine:
                return False
            
            # Test connection
            from sqlalchemy import text
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def async_health_check(self) -> bool:
        """
        Perform async health check on the connection pool
        """
        try:
            if not self.async_engine:
                return False
            
            from sqlalchemy import text
            async with self.async_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            return True
        except Exception as e:
            logger.error(f"Async database health check failed: {e}")
            return False
    
    def close(self):
        """
        Close all connections and cleanup
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Synchronous database connections closed")
        
        if self.async_engine:
            asyncio.create_task(self.async_engine.dispose())
            logger.info("Asynchronous database connections closed")

# Global connection pool instance
connection_pool = OptimizedConnectionPool()

def initialize_database_pool(database_url: str):
    """
    Initialize the global database connection pool
    """
    connection_pool.initialize(database_url)

def get_connection_pool() -> OptimizedConnectionPool:
    """
    Get the global connection pool instance
    """
    return connection_pool

async def get_db_session():
    """
    Dependency to get database session
    """
    async with connection_pool.get_async_session() as session:
        yield session

def get_sync_db_session():
    """
    Get synchronous database session
    """
    return connection_pool.get_sync_session()

# Connection pool monitoring
class ConnectionPoolMonitor:
    """
    Monitor connection pool health and performance
    """
    
    def __init__(self, pool: OptimizedConnectionPool):
        self.pool = pool
        self.monitoring = False
        self._monitor_task = None
    
    async def start_monitoring(self, interval: int = 30):
        """
        Start monitoring connection pool
        """
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Connection pool monitoring started")
    
    async def stop_monitoring(self):
        """
        Stop monitoring connection pool
        """
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Connection pool monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """
        Monitoring loop
        """
        while self.monitoring:
            try:
                stats = self.pool.get_connection_stats()
                health = await self.pool.async_health_check()
                
                # Log statistics
                logger.info(f"Connection pool stats: {stats}")
                
                # Check for issues
                if stats.get("utilization_percent", 0) > 80:
                    logger.warning(f"High connection pool utilization: {stats['utilization_percent']:.1f}%")
                
                if not health:
                    logger.error("Database health check failed")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in connection pool monitoring: {e}")
                await asyncio.sleep(interval)

# Global monitor instance
pool_monitor = ConnectionPoolMonitor(connection_pool)
