"""
Rate Limiting Middleware for FastAPI
Prevents abuse by limiting requests per IP address and endpoint.
"""

import time
from collections import defaultdict, deque
from typing import Dict

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import log


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware that tracks requests per IP and endpoint.
    Uses sliding window algorithm for more accurate rate limiting.
    """
    
    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        burst_limit: int = 10,
        window_size: int = 60,  # seconds
        blocked_duration: int = 300,  # 5 minutes
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.burst_limit = burst_limit
        self.window_size = window_size
        self.blocked_duration = blocked_duration
        
        # Store request timestamps per IP
        self.request_history: Dict[str, deque] = defaultdict(deque)
        self.blocked_ips: Dict[str, float] = {}
        
        # Special limits for problematic endpoints
        self.endpoint_limits = {
            "/api/v1/subscription/check-feature-access": {
                "requests_per_minute": 5,
                "requests_per_hour": 50,
                "burst_limit": 3,
            }
        }
        
        # Cleanup old entries every 5 minutes
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded IP first (for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        return getattr(request.client, 'host', 'unknown')
    
    def _is_blocked(self, client_ip: str) -> bool:
        """Check if IP is currently blocked."""
        if client_ip in self.blocked_ips:
            if time.time() - self.blocked_ips[client_ip] < self.blocked_duration:
                return True
            else:
                # Unblock expired IPs
                del self.blocked_ips[client_ip]
        return False
    
    def _cleanup_old_entries(self):
        """Clean up old request history entries."""
        current_time = time.time()
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        self.last_cleanup = current_time
        cutoff_time = current_time - (self.window_size * 2)  # Keep 2 windows worth of data
        
        # Clean up request history
        for ip in list(self.request_history.keys()):
            history = self.request_history[ip]
            # Remove old entries
            while history and history[0] < cutoff_time:
                history.popleft()
            
            # Remove empty histories
            if not history:
                del self.request_history[ip]
        
        # Clean up blocked IPs
        for ip in list(self.blocked_ips.keys()):
            if current_time - self.blocked_ips[ip] >= self.blocked_duration:
                del self.blocked_ips[ip]
    
    def _check_rate_limit(self, client_ip: str, endpoint: str) -> tuple[bool, str]:
        """
        Check if request should be rate limited.
        Returns (is_allowed, reason)
        """
        current_time = time.time()
        
        # Get endpoint-specific limits or use defaults
        limits = self.endpoint_limits.get(endpoint, {
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "burst_limit": self.burst_limit,
        })
        
        # Get request history for this IP
        history = self.request_history[client_ip]
        
        # Remove old entries (older than window_size)
        while history and history[0] < current_time - self.window_size:
            history.popleft()
        
        # Check burst limit (requests in last 10 seconds)
        recent_requests = sum(1 for timestamp in history if timestamp > current_time - 10)
        if recent_requests >= limits["burst_limit"]:
            return False, f"Burst limit exceeded: {recent_requests}/{limits['burst_limit']} requests in last 10 seconds"
        
        # Check per-minute limit
        minute_requests = sum(1 for timestamp in history if timestamp > current_time - 60)
        if minute_requests >= limits["requests_per_minute"]:
            return False, f"Rate limit exceeded: {minute_requests}/{limits['requests_per_minute']} requests per minute"
        
        # Check per-hour limit
        hour_requests = sum(1 for timestamp in history if timestamp > current_time - 3600)
        if hour_requests >= limits["requests_per_hour"]:
            return False, f"Rate limit exceeded: {hour_requests}/{limits['requests_per_hour']} requests per hour"
        
        # Add current request to history
        history.append(current_time)
        
        return True, "OK"
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and apply rate limiting."""
        client_ip = self._get_client_ip(request)
        endpoint = request.url.path
        
        # Skip rate limiting for health checks and static files
        if endpoint in ["/health", "/docs", "/openapi.json", "/favicon.ico"]:
            return await call_next(request)
        
        # Clean up old entries periodically
        self._cleanup_old_entries()
        
        # Check if IP is blocked
        if self._is_blocked(client_ip):
            log.logs.warning(f"Blocked IP {client_ip} attempted to access {endpoint}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "IP temporarily blocked",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": self.blocked_duration
                },
                headers={"Retry-After": str(self.blocked_duration)}
            )
        
        # Check rate limits
        is_allowed, reason = self._check_rate_limit(client_ip, endpoint)
        
        if not is_allowed:
            # Log the rate limit violation
            log.logs.warning(f"Rate limit exceeded for {client_ip} on {endpoint}: {reason}")
            
            # Block IP if it's a problematic endpoint
            if endpoint in self.endpoint_limits:
                self.blocked_ips[client_ip] = time.time()
                log.logs.warning(f"Blocked IP {client_ip} for {self.blocked_duration} seconds due to abuse of {endpoint}")
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": reason,
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        history = self.request_history[client_ip]
        current_time = time.time()
        
        # Calculate remaining requests
        minute_requests = sum(1 for timestamp in history if timestamp > current_time - 60)
        hour_requests = sum(1 for timestamp in history if timestamp > current_time - 3600)
        
        limits = self.endpoint_limits.get(endpoint, {
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
        })
        
        response.headers["X-RateLimit-Limit-Minute"] = str(limits["requests_per_minute"])
        response.headers["X-RateLimit-Remaining-Minute"] = str(max(0, limits["requests_per_minute"] - minute_requests))
        response.headers["X-RateLimit-Limit-Hour"] = str(limits["requests_per_hour"])
        response.headers["X-RateLimit-Remaining-Hour"] = str(max(0, limits["requests_per_hour"] - hour_requests))
        
        return response
    
    def get_stats(self) -> Dict:
        """Get current rate limiting statistics."""
        current_time = time.time()
        
        stats = {
            "total_tracked_ips": len(self.request_history),
            "blocked_ips": len(self.blocked_ips),
            "active_requests_last_minute": 0,
            "active_requests_last_hour": 0,
        }
        
        for ip, history in self.request_history.items():
            minute_requests = sum(1 for timestamp in history if timestamp > current_time - 60)
            hour_requests = sum(1 for timestamp in history if timestamp > current_time - 3600)
            stats["active_requests_last_minute"] += minute_requests
            stats["active_requests_last_hour"] += hour_requests
        
        return stats
