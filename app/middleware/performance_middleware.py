"""
Performance middleware for 2 vCPU + 8GB RAM server optimization
"""
import logging
import time
from typing import Any, Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.config.server import RATE_LIMITS

logger = logging.getLogger(__name__)

class PerformanceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track and optimize performance
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_count = 0
        self.active_requests = 0
        self.max_concurrent_requests = RATE_LIMITS["concurrent_requests"]
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Process request with performance tracking
        """
        # Check concurrent request limit
        if self.active_requests >= self.max_concurrent_requests:
            logger.warning(f"Concurrent request limit reached: {self.active_requests}")
            return Response(
                content="Server busy, please try again later",
                status_code=503,
                headers={"Retry-After": "5"}
            )
        
        # Track request start
        start_time = time.time()
        self.active_requests += 1
        self.request_count += 1
        
        # Add performance headers
        request.state.start_time = start_time
        request.state.request_id = f"req_{self.request_count}_{int(start_time)}"
        
        performance_monitor = None
        try:
            from app.utils.monitoring.performance_monitor import (
                performance_monitor as pm,
            )
            performance_monitor = pm
        except (ImportError, Exception) as e:
            logger.debug(f"Performance monitor not available: {e}")
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate performance metrics
            process_time = time.time() - start_time
            is_error = response.status_code >= 400
            
            # Record metrics if available
            if performance_monitor is not None:
                try:
                    performance_monitor.record_request(process_time * 1000, is_error)
                except Exception as e:
                    logger.debug(f"Failed to record performance metrics: {e}")
            
            # Add performance headers to response
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request.state.request_id
            response.headers["X-Active-Requests"] = str(self.active_requests)
            
            # Log slow requests
            if process_time > 1.0:  # 1 second threshold
                logger.warning(f"Slow request: {request.method} {request.url.path} "
                             f"took {process_time:.2f}s")
            
            return response
            
        except Exception as e:
            # Record error
            process_time = time.time() - start_time
            if performance_monitor is not None:
                try:
                    performance_monitor.record_request(process_time * 1000, True)
                except Exception as record_error:
                    logger.debug(f"Failed to record error metrics: {record_error}")
            
            logger.error(f"Request error: {request.method} {request.url.path} "
                        f"took {process_time:.2f}s - {str(e)}")
            raise
            
        finally:
            self.active_requests -= 1

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_counts: Dict[str, Dict[str, Any]] = {}
        self.burst_counts: Dict[str, int] = {}
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Apply rate limiting
        """
        client_ip = getattr(request.client, 'host', 'unknown')
        current_time = time.time()
        
        # Initialize client tracking
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {
                "minute_requests": [],
                "hour_requests": [],
                "blocked_until": 0
            }
        
        client_data = self.request_counts[client_ip]
        
        # Check if client is blocked
        if current_time < client_data["blocked_until"]:
            return Response(
                content="Rate limit exceeded, please try again later",
                status_code=429,
                headers={
                    "Retry-After": str(int(client_data["blocked_until"] - current_time)),
                    "X-RateLimit-Limit": str(RATE_LIMITS["per_minute"]),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Clean old requests
        minute_ago = current_time - 60
        hour_ago = current_time - 3600
        
        client_data["minute_requests"] = [
            req_time for req_time in client_data["minute_requests"] 
            if req_time > minute_ago
        ]
        client_data["hour_requests"] = [
            req_time for req_time in client_data["hour_requests"] 
            if req_time > hour_ago
        ]
        
        # Check rate limits
        minute_requests = len(client_data["minute_requests"])
        hour_requests = len(client_data["hour_requests"])
        
        # Check burst limit
        if client_ip not in self.burst_counts:
            self.burst_counts[client_ip] = 0
        
        # Reset burst count if enough time has passed
        if current_time - (self.burst_counts.get(f"{client_ip}_last_reset", 0)) > 60:
            self.burst_counts[client_ip] = 0
            self.burst_counts[f"{client_ip}_last_reset"] = int(current_time)
        
        # Check limits
        if minute_requests >= RATE_LIMITS["per_minute"]:
            client_data["blocked_until"] = current_time + RATE_LIMITS["block_duration"]
            logger.warning(f"Rate limit exceeded for {client_ip}: {minute_requests} requests/minute")
            return Response(
                content="Rate limit exceeded, please try again later",
                status_code=429,
                headers={
                    "Retry-After": str(RATE_LIMITS["block_duration"]),
                    "X-RateLimit-Limit": str(RATE_LIMITS["per_minute"]),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        if hour_requests >= RATE_LIMITS["per_hour"]:
            client_data["blocked_until"] = current_time + RATE_LIMITS["block_duration"]
            logger.warning(f"Hourly rate limit exceeded for {client_ip}: {hour_requests} requests/hour")
            return Response(
                content="Hourly rate limit exceeded, please try again later",
                status_code=429,
                headers={
                    "Retry-After": str(RATE_LIMITS["block_duration"]),
                    "X-RateLimit-Limit": str(RATE_LIMITS["per_hour"]),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        if self.burst_counts[client_ip] >= RATE_LIMITS["burst_limit"]:
            logger.warning(f"Burst limit exceeded for {client_ip}")
            return Response(
                content="Too many requests in burst, please slow down",
                status_code=429,
                headers={
                    "Retry-After": "10",
                    "X-RateLimit-Limit": str(RATE_LIMITS["burst_limit"]),
                    "X-RateLimit-Remaining": "0"
                }
            )
        
        # Record request
        client_data["minute_requests"].append(current_time)
        client_data["hour_requests"].append(current_time)
        self.burst_counts[client_ip] += 1
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        remaining_minute = RATE_LIMITS["per_minute"] - minute_requests - 1
        remaining_hour = RATE_LIMITS["per_hour"] - hour_requests - 1
        
        response.headers["X-RateLimit-Limit"] = str(RATE_LIMITS["per_minute"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining_minute))
        response.headers["X-RateLimit-Reset"] = str(int(current_time + 60))
        response.headers["X-RateLimit-Hourly-Limit"] = str(RATE_LIMITS["per_hour"])
        response.headers["X-RateLimit-Hourly-Remaining"] = str(max(0, remaining_hour))
        
        return response

class MemoryOptimizationMiddleware(BaseHTTPMiddleware):
    """
    Memory optimization middleware
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.request_size_limit = 10 * 1024 * 1024  # 10MB
        self.response_size_limit = 50 * 1024 * 1024  # 50MB
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Apply memory optimizations
        """
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.request_size_limit:
            logger.warning(f"Large request size: {content_length} bytes")
            return Response(
                content="Request too large",
                status_code=413,
                headers={"Retry-After": "5"}
            )
        
        # Process request
        response = await call_next(request)
        
        # Check response size
        response_size = response.headers.get("content-length")
        if response_size and int(response_size) > self.response_size_limit:
            logger.warning(f"Large response size: {response_size} bytes")
        
        # Add memory optimization headers
        response.headers["X-Memory-Optimized"] = "true"
        response.headers["X-Request-Size-Limit"] = str(self.request_size_limit)
        response.headers["X-Response-Size-Limit"] = str(self.response_size_limit)
        
        return response

class CompressionMiddleware(BaseHTTPMiddleware):
    """
    Compression middleware for response optimization
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.min_size = 1024  # 1KB minimum size for compression
        self.compression_level = 6  # Balanced compression
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Apply compression to responses
        """
        # Check if client accepts compression
        accept_encoding = request.headers.get("accept-encoding", "")
        supports_gzip = "gzip" in accept_encoding
        supports_deflate = "deflate" in accept_encoding
        
        if not (supports_gzip or supports_deflate):
            return await call_next(request)
        
        # Process request
        response = await call_next(request)
        
        # Check if response should be compressed
        content_type = response.headers.get("content-type", "")
        content_length = response.headers.get("content-length")
        
        # Skip compression for certain content types
        skip_types = ["image/", "video/", "audio/", "application/zip", "application/gzip"]
        if any(content_type.startswith(skip_type) for skip_type in skip_types):
            return response
        
        # Skip compression for small responses
        if content_length and int(content_length) < self.min_size:
            return response
        
        # Add compression headers
        if supports_gzip:
            response.headers["Content-Encoding"] = "gzip"
        elif supports_deflate:
            response.headers["Content-Encoding"] = "deflate"
        
        response.headers["X-Compression-Level"] = str(self.compression_level)
        response.headers["X-Compression-Min-Size"] = str(self.min_size)
        
        return response

class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Cache control middleware
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.cache_rules = {
            "/static/": {"max_age": 3600, "public": True},  # 1 hour
            "/api/health": {"max_age": 60, "public": True},  # 1 minute
            "/api/metrics": {"max_age": 30, "public": False},  # 30 seconds
        }
        
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """
        Apply cache control headers
        """
        response = await call_next(request)
        
        # Apply cache rules based on path
        path = request.url.path
        for pattern, cache_config in self.cache_rules.items():
            if path.startswith(pattern):
                max_age = cache_config["max_age"]
                is_public = cache_config["public"]
                
                cache_control = f"{'public' if is_public else 'private'}, max-age={max_age}"
                response.headers["Cache-Control"] = cache_control
                response.headers["X-Cache-Rule"] = pattern
                break
        
        return response

# Middleware stack for optimal performance
def create_middleware_stack(app: ASGIApp) -> ASGIApp:
    """
    Create optimized middleware stack
    """
    # Apply middleware in order (last applied is outermost)
    app = CacheControlMiddleware(app)
    app = CompressionMiddleware(app)
    app = MemoryOptimizationMiddleware(app)
    app = RateLimitMiddleware(app)
    app = PerformanceMiddleware(app)
    
    return app