"""
Optimized database connection pool configuration for high-performance operations.
Based on performance analysis showing database execution as the primary bottleneck.
"""

import asyncio
import time
from typing import Any, Dict, Optional

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.utils.logger import log


class OptimizedDatabasePool:
    """Optimized database connection pool with performance monitoring"""
    
    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.pool_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "overflow_connections": 0,
            "connection_waits": 0,
            "connection_errors": 0
        }
        self.last_stats_time = time.time()
    
    def create_optimized_engine(self, database_url: str, **kwargs) -> AsyncEngine:
        """
        Create an optimized database engine with performance-tuned pool settings.
        
        Based on performance analysis:
        - Database execution is 95-97% of total request time
        - Current pool: 20 base + 40 overflow = 60 max connections
        - For 4GB RAM system, optimize for memory efficiency
        """
        
        # Optimized configuration for 4GB RAM system with NullPool
        optimized_config = {
            # Performance optimizations
            "echo": kwargs.get("echo", False),  # Disable SQL logging in production
            "future": True,  # Use SQLAlchemy 2.0 style
            
            # Connection pool class optimization (NullPool doesn't support pool_size, max_overflow, etc.)
            "poolclass": NullPool,
        }
            
        # Merge with any provided kwargs
        optimized_config.update(kwargs)

        # Database specific connect_args
        if "sqlite" in database_url:
            optimized_config["connect_args"] = {"check_same_thread": False}
        elif "connect_args" not in optimized_config:
            optimized_config["connect_args"] = {
                "command_timeout": 30,  # 30 second command timeout
                "server_settings": {
                    "application_name": "smart_helmet_optimized",
                    "tcp_keepalives_idle": "600",  # 10 minutes
                    "tcp_keepalives_interval": "30",  # 30 seconds
                    "tcp_keepalives_count": "3",
                }
            }
        
        log.logs.info("🔧 [POOL] Creating optimized engine with NullPool for async compatibility")
        
        self.engine = create_async_engine(database_url, **optimized_config)
        
        # Add event listeners for monitoring
        self._add_pool_monitoring()
        
        return self.engine
    
    def _add_pool_monitoring(self):
        """Add event listeners to monitor pool performance"""
        if not self.engine:
            return
            
        @event.listens_for(self.engine.sync_engine, "connect")
        def on_connect(dbapi_connection, connection_record):
            """Monitor new connections"""
            self.pool_stats["total_connections"] += 1
            log.logs.debug("🔗 [POOL] New connection created")
        
        @event.listens_for(self.engine.sync_engine, "checkout")
        def on_checkout(dbapi_connection, connection_record, connection_proxy):
            """Monitor connection checkout"""
            self.pool_stats["active_connections"] += 1
            log.logs.debug("📤 [POOL] Connection checked out")
        
        @event.listens_for(self.engine.sync_engine, "checkin")
        def on_checkin(dbapi_connection, connection_record):
            """Monitor connection checkin"""
            self.pool_stats["active_connections"] = max(0, self.pool_stats["active_connections"] - 1)
            log.logs.debug("📥 [POOL] Connection checked in")
    
    def get_pool_status(self) -> Dict[str, Any]:
        """Get current pool status and statistics"""
        if not self.engine:
            return {"error": "Engine not initialized"}
        
        try:
            pool = self.engine.pool
            
            # Get pool statistics
            pool_size = getattr(pool, 'size', lambda: 0)()
            checked_in = getattr(pool, 'checkedin', lambda: 0)()
            checked_out = getattr(pool, 'checkedout', lambda: 0)()
            overflow = getattr(pool, 'overflow', lambda: 0)()
            
            # Calculate additional metrics
            total_connections = pool_size + overflow
            idle_connections = checked_in
            active_connections = checked_out
            
            # Calculate utilization
            utilization = (active_connections / total_connections * 100) if total_connections > 0 else 0
            
            status = {
                "pool_size": pool_size,
                "max_overflow": getattr(pool, '_max_overflow', 0),
                "total_connections": total_connections,
                "active_connections": active_connections,
                "idle_connections": idle_connections,
                "overflow_connections": overflow,
                "utilization_percentage": round(utilization, 2),
                "checked_in": checked_in,
                "checked_out": checked_out,
                "pool_timeout": getattr(pool, '_timeout', 0),
                "pool_recycle": getattr(pool, '_recycle', 0)
            }
            
            return status
            
        except Exception as e:
            log.logs.error(f"❌ [POOL] Error getting pool status: {e}")
            return {"error": str(e)}
    
    def log_pool_performance(self):
        """Log pool performance metrics"""
        status = self.get_pool_status()
        
        if "error" not in status:
            log.logs.info("🔗 [POOL] Connection Pool Status:")
            log.logs.info(f"   📊 Pool Size: {status['pool_size']}")
            log.logs.info(f"   📈 Max Overflow: {status['max_overflow']}")
            log.logs.info(f"   🔢 Total Connections: {status['total_connections']}")
            log.logs.info(f"   ✅ Active: {status['active_connections']}")
            log.logs.info(f"   💤 Idle: {status['idle_connections']}")
            log.logs.info(f"   ⚡ Overflow: {status['overflow_connections']}")
            log.logs.info(f"   📊 Utilization: {status['utilization_percentage']}%")
    
    async def health_check(self) -> bool:
        """Perform a health check on the database connection"""
        if not self.engine:
            return False
        
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            log.logs.error(f"❌ [POOL] Health check failed: {e}")
            return False
    
    async def close(self):
        """Close the database engine and cleanup"""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            log.logs.info("🔒 [POOL] Database engine closed")


# Global optimized pool instance
optimized_pool = OptimizedDatabasePool()


def get_optimized_pool_config() -> Dict[str, Any]:
    """
    Get optimized pool configuration based on system resources.
    Returns configuration suitable for 4GB RAM system with NullPool.
    """
    return {
        "echo": False,  # Disable SQL logging
        "future": True,  # Use SQLAlchemy 2.0 style
        "poolclass": NullPool,
        "connect_args": {
            "command_timeout": 30,
            "server_settings": {
                "application_name": "junehs_optimized",
                "tcp_keepalives_idle": "600",
                "tcp_keepalives_interval": "30",
                "tcp_keepalives_count": "3",
            }
        }
    }


async def monitor_pool_performance():
    """Background task to monitor pool performance"""
    while True:
        try:
            optimized_pool.log_pool_performance()
            await asyncio.sleep(300)  # Log every 5 minutes
        except Exception as e:
            log.logs.error(f"❌ [POOL] Performance monitoring error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute before retry
