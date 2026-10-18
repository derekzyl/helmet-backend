"""
Server-specific configuration for 2 vCPU + 8GB RAM setup
"""
import os
from typing import Any, Dict

# Server Hardware Configuration
SERVER_CONFIG = {
    "cpu_cores": 2,
    "total_memory_gb": 4,
    "available_memory_gb": 3,  # Leave 1GB for system
    "worker_processes": 2,     # Match CPU cores
    "worker_connections": 1000,
    "timeout": 30,
    "keepalive": 2,
}

# Database Connection Pool Configuration
DATABASE_POOL_CONFIG = {
    "pool_size": 5,            # Reduced for 4GB RAM: 2 vCPU * 2.5 = 5 connections
    "max_overflow": 10,        # Additional connections when needed
    "pool_timeout": 30,        # Wait time for connection
    "pool_recycle": 3600,      # Recycle connections every hour
    "pool_pre_ping": True,     # Verify connections before use
    "echo": False,             # Disable SQL logging in production
}

# Redis Configuration
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "password": os.getenv("REDIS_PASSWORD"),
    "max_connections": 25,     # Reduced for 4GB RAM: 2 vCPU * 12.5 = 25 connections
    "retry_on_timeout": True,
    "socket_keepalive": True,
    "socket_keepalive_options": {},
    "health_check_interval": 30,
    "decode_responses": True,
}

# Memory Management Configuration
MEMORY_CONFIG = {
    "max_cache_size": "1GB",      # 25% of total RAM (4GB)
    "query_cache_size": "256MB",  # 6.25% of total RAM
    "session_cache_size": "128MB", # 3.125% of total RAM
    "temp_buffer_size": "64MB",   # 1.56% of total RAM
    "gc_threshold": (700, 10, 10), # Aggressive garbage collection
    "memory_profiling": True,      # Monitor memory usage
    "memory_limit": "3GB",        # Leave 1GB for system
}

# Caching Configuration
CACHE_CONFIG = {
    "default_ttl": 300,           # 5 minutes
    "max_memory": "1GB",          # 25% of RAM (4GB)
    "eviction_policy": "lru",     # Least Recently Used
    "compression": True,          # Compress cached data
    "serialization": "pickle",    # Fast serialization
    "key_prefix": "app:",
    "namespace_separator": ":",
}

# Rate Limiting Configuration
RATE_LIMITS = {
    "per_minute": 60,            # Reduced for 4GB RAM: 60 requests per minute per IP
    "per_hour": 600,             # Reduced for 4GB RAM: 600 requests per hour per IP
    "burst_limit": 15,           # Reduced for 4GB RAM: 15 requests in burst
    "concurrent_requests": 30,   # Reduced for 4GB RAM: 30 concurrent requests max
    "window_size": 60,           # 60 second window
    "block_duration": 300,       # 5 minute block duration
}

# Performance Monitoring Configuration
PERFORMANCE_CONFIG = {
    "enable_monitoring": True,
    "metrics_interval": 30,      # 30 seconds
    "slow_query_threshold": 1.0, # 1 second
    "memory_alert_threshold": 3.2, # 3.2GB (80% of 4GB)
    "cpu_alert_threshold": 80,   # 80% CPU usage
    "log_slow_queries": True,
    "log_memory_usage": True,
    "log_performance_metrics": True,
}

# API Configuration
API_CONFIG = {
    "max_request_size": "10MB",
    "request_timeout": 30,
    "response_timeout": 30,
    "max_concurrent_requests": 50,
    "enable_compression": True,
    "compression_level": 6,
    "enable_cors": True,
    "cors_origins": ["*"],  # Configure appropriately for production
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file_rotation": True,
    "max_file_size": "100MB",
    "backup_count": 5,
    "log_sql_queries": False,  # Disable in production
    "log_performance": True,
}

# Security Configuration
SECURITY_CONFIG = {
    "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "password_min_length": 8,
    "max_login_attempts": 5,
    "lockout_duration": 300,  # 5 minutes
}

def get_optimized_config() -> Dict[str, Any]:
    """
    Get optimized configuration for 2 vCPU + 8GB RAM server
    """
    return {
        "server": SERVER_CONFIG,
        "database": DATABASE_POOL_CONFIG,
        "redis": REDIS_CONFIG,
        "memory": MEMORY_CONFIG,
        "cache": CACHE_CONFIG,
        "rate_limits": RATE_LIMITS,
        "performance": PERFORMANCE_CONFIG,
        "api": API_CONFIG,
        "logging": LOGGING_CONFIG,
        "security": SECURITY_CONFIG,
    }

def get_worker_config() -> Dict[str, Any]:
    """
    Get Gunicorn/Uvicorn worker configuration
    """
    return {
        "workers": SERVER_CONFIG["worker_processes"],
        "worker_class": "uvicorn.workers.UvicornWorker",
        "worker_connections": SERVER_CONFIG["worker_connections"],
        "timeout": SERVER_CONFIG["timeout"],
        "keepalive": SERVER_CONFIG["keepalive"],
        "max_requests": 1000,
        "max_requests_jitter": 100,
        "preload_app": True,
        "bind": "0.0.0.0:8000",
    }

def get_database_url() -> str:
    """
    Get optimized database URL with connection pooling
    """
    base_url = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
    
    # Add connection pooling parameters
    pool_params = [
        f"pool_size={DATABASE_POOL_CONFIG['pool_size']}",
        f"max_overflow={DATABASE_POOL_CONFIG['max_overflow']}",
        f"pool_timeout={DATABASE_POOL_CONFIG['pool_timeout']}",
        f"pool_recycle={DATABASE_POOL_CONFIG['pool_recycle']}",
        f"pool_pre_ping={DATABASE_POOL_CONFIG['pool_pre_ping']}",
    ]
    
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{'&'.join(pool_params)}"

def get_redis_url() -> str:
    """
    Get Redis URL with optimized parameters
    """
    host = REDIS_CONFIG["host"]
    port = REDIS_CONFIG["port"]
    db = REDIS_CONFIG["db"]
    password = REDIS_CONFIG["password"]
    
    if password:
        return f"redis://:{password}@{host}:{port}/{db}"
    else:
        return f"redis://{host}:{port}/{db}"

# Environment-specific configurations
DEVELOPMENT_CONFIG = {
    "debug": True,
    "reload": True,
    "log_level": "DEBUG",
    "enable_profiling": True,
}

PRODUCTION_CONFIG = {
    "debug": False,
    "reload": False,
    "log_level": "INFO",
    "enable_profiling": False,
    "ssl_redirect": True,
    "secure_cookies": True,
}

def get_environment_config() -> Dict[str, Any]:
    """
    Get environment-specific configuration
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return PRODUCTION_CONFIG
    else:
        return DEVELOPMENT_CONFIG
