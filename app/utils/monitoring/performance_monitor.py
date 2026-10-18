"""
Performance monitoring for 2 vCPU + 8GB RAM server
"""
import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Lazy import psutil to avoid circular import issues
_psutil: Any = None
_PSUTIL_UNAVAILABLE = object()  # Sentinel object to indicate psutil is unavailable

def _get_psutil():
    """Lazy import psutil to avoid circular import issues"""
    global _psutil
    if _psutil is None:
        try:
            import psutil
            _psutil = psutil
        except ImportError as e:
            logger.warning(f"psutil not available: {e}. Performance monitoring will be limited.")
            _psutil = _PSUTIL_UNAVAILABLE  # Use sentinel to indicate unavailable
    return _psutil if _psutil is not _PSUTIL_UNAVAILABLE else None

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics data structure"""
    timestamp: datetime
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_available_gb: float
    disk_io_read: int
    disk_io_write: int
    network_sent: int
    network_recv: int
    active_connections: int
    response_time_avg: float
    requests_per_second: float
    error_rate: float
    cache_hit_rate: float
    database_connections: int
    database_query_time: float

@dataclass
class AlertThresholds:
    """Alert thresholds for monitoring"""
    cpu_percent: float = 80.0
    memory_percent: float = 85.0
    memory_used_gb: float = 6.0
    response_time_ms: float = 1000.0
    error_rate_percent: float = 5.0
    cache_hit_rate_percent: float = 70.0
    database_query_time_ms: float = 1000.0

class PerformanceMonitor:
    """
    Performance monitor for 2 vCPU + 8GB RAM server
    """
    
    def __init__(self, alert_thresholds: Optional[AlertThresholds] = None):
        self.alert_thresholds = alert_thresholds or AlertThresholds()
        self.metrics_history: deque = deque(maxlen=1000)  # Keep last 1000 metrics
        self.alerts: List[Dict[str, Any]] = []
        self.monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._start_time = time.time()
        self._request_count = 0
        self._error_count = 0
        self._response_times: deque = deque(maxlen=100)
        
        # Initialize baseline metrics
        self._baseline_metrics = self._get_system_metrics()
        
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get current system metrics"""
        psutil_module = _get_psutil()
        if psutil_module is None:
            # Return default values if psutil is not available
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_used_gb": 0.0,
                "memory_available_gb": 0.0,
                "disk_io_read": 0,
                "disk_io_write": 0,
                "network_sent": 0,
                "network_recv": 0,
                "active_connections": 0,
            }
        
        try:
            # CPU and Memory
            cpu_percent = psutil_module.cpu_percent(interval=1)
            memory = psutil_module.virtual_memory()
            memory_percent = memory.percent
            memory_used_gb = memory.used / (1024**3)
            memory_available_gb = memory.available / (1024**3)
            
            # Disk I/O
            disk_io = psutil_module.disk_io_counters()
            disk_io_read = disk_io.read_bytes if disk_io else 0
            disk_io_write = disk_io.write_bytes if disk_io else 0
            
            # Network I/O
            network_io = psutil_module.net_io_counters()
            network_sent = network_io.bytes_sent if network_io else 0
            network_recv = network_io.bytes_recv if network_io else 0
            
            # Active connections
            connections = len(psutil_module.net_connections())
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "memory_used_gb": memory_used_gb,
                "memory_available_gb": memory_available_gb,
                "disk_io_read": disk_io_read,
                "disk_io_write": disk_io_write,
                "network_sent": network_sent,
                "network_recv": network_recv,
                "active_connections": connections,
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_used_gb": 0.0,
                "memory_available_gb": 0.0,
                "disk_io_read": 0,
                "disk_io_write": 0,
                "network_sent": 0,
                "network_recv": 0,
                "active_connections": 0,
            }
    
    def _calculate_application_metrics(self) -> Dict[str, Any]:
        """Calculate application-specific metrics"""
        try:
            # Response time average
            response_time_avg = 0.0
            if self._response_times:
                response_time_avg = sum(self._response_times) / len(self._response_times)
            
            # Requests per second
            uptime = time.time() - self._start_time
            requests_per_second = self._request_count / uptime if uptime > 0 else 0
            
            # Error rate
            error_rate = (self._error_count / self._request_count * 100) if self._request_count > 0 else 0
            
            return {
                "response_time_avg": response_time_avg,
                "requests_per_second": requests_per_second,
                "error_rate": error_rate,
                "cache_hit_rate": 0.0,  # Will be updated by cache monitor
                "database_connections": 0,  # Will be updated by database monitor
                "database_query_time": 0.0,  # Will be updated by database monitor
            }
        except Exception as e:
            logger.error(f"Error calculating application metrics: {e}")
            return {}
    
    def record_request(self, response_time: float, is_error: bool = False):
        """Record a request for metrics calculation"""
        self._request_count += 1
        if is_error:
            self._error_count += 1
        self._response_times.append(response_time)
    
    def update_cache_metrics(self, hit_rate: float):
        """Update cache hit rate metrics"""
        # This will be called by cache monitor
        pass
    
    def update_database_metrics(self, connections: int, query_time: float):
        """Update database metrics"""
        # This will be called by database monitor
        pass
    
    async def collect_metrics(self) -> PerformanceMetrics:
        """Collect current performance metrics"""
        system_metrics = self._get_system_metrics()
        app_metrics = self._calculate_application_metrics()
        
        metrics = PerformanceMetrics(
            timestamp=datetime.now(),
            **system_metrics,
            **app_metrics
        )
        
        self.metrics_history.append(metrics)
        return metrics
    
    def check_alerts(self, metrics: PerformanceMetrics) -> List[Dict[str, Any]]:
        """Check for alert conditions"""
        new_alerts = []
        
        # CPU alert
        if metrics.cpu_percent > self.alert_thresholds.cpu_percent:
            new_alerts.append({
                "type": "cpu_high",
                "message": f"High CPU usage: {metrics.cpu_percent:.1f}%",
                "value": metrics.cpu_percent,
                "threshold": self.alert_thresholds.cpu_percent,
                "timestamp": metrics.timestamp
            })
        
        # Memory alert
        if metrics.memory_percent > self.alert_thresholds.memory_percent:
            new_alerts.append({
                "type": "memory_high",
                "message": f"High memory usage: {metrics.memory_percent:.1f}%",
                "value": metrics.memory_percent,
                "threshold": self.alert_thresholds.memory_percent,
                "timestamp": metrics.timestamp
            })
        
        # Memory usage in GB alert
        if metrics.memory_used_gb > self.alert_thresholds.memory_used_gb:
            new_alerts.append({
                "type": "memory_gb_high",
                "message": f"High memory usage: {metrics.memory_used_gb:.1f}GB",
                "value": metrics.memory_used_gb,
                "threshold": self.alert_thresholds.memory_used_gb,
                "timestamp": metrics.timestamp
            })
        
        # Response time alert
        if metrics.response_time_avg > self.alert_thresholds.response_time_ms:
            new_alerts.append({
                "type": "response_time_high",
                "message": f"High response time: {metrics.response_time_avg:.1f}ms",
                "value": metrics.response_time_avg,
                "threshold": self.alert_thresholds.response_time_ms,
                "timestamp": metrics.timestamp
            })
        
        # Error rate alert
        if metrics.error_rate > self.alert_thresholds.error_rate_percent:
            new_alerts.append({
                "type": "error_rate_high",
                "message": f"High error rate: {metrics.error_rate:.1f}%",
                "value": metrics.error_rate,
                "threshold": self.alert_thresholds.error_rate_percent,
                "timestamp": metrics.timestamp
            })
        
        # Cache hit rate alert
        if metrics.cache_hit_rate < self.alert_thresholds.cache_hit_rate_percent:
            new_alerts.append({
                "type": "cache_hit_rate_low",
                "message": f"Low cache hit rate: {metrics.cache_hit_rate:.1f}%",
                "value": metrics.cache_hit_rate,
                "threshold": self.alert_thresholds.cache_hit_rate_percent,
                "timestamp": metrics.timestamp
            })
        
        # Database query time alert
        if metrics.database_query_time > self.alert_thresholds.database_query_time_ms:
            new_alerts.append({
                "type": "database_query_slow",
                "message": f"Slow database query: {metrics.database_query_time:.1f}ms",
                "value": metrics.database_query_time,
                "threshold": self.alert_thresholds.database_query_time_ms,
                "timestamp": metrics.timestamp
            })
        
        # Add new alerts to the list
        self.alerts.extend(new_alerts)
        
        # Log alerts
        for alert in new_alerts:
            logger.warning(f"ALERT: {alert['message']}")
        
        return new_alerts
    
    async def start_monitoring(self, interval: int = 30):
        """Start performance monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if not self.monitoring:
            return
        
        self.monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Performance monitoring stopped")
    
    async def _monitor_loop(self, interval: int):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                metrics = await self.collect_metrics()
                alerts = self.check_alerts(metrics)
                
                # Log metrics every 5 minutes
                if len(self.metrics_history) % 10 == 0:
                    logger.info(f"Performance metrics: CPU={metrics.cpu_percent:.1f}%, "
                              f"Memory={metrics.memory_percent:.1f}% ({metrics.memory_used_gb:.1f}GB), "
                              f"RPS={metrics.requests_per_second:.1f}, "
                              f"Response={metrics.response_time_avg:.1f}ms")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}")
                await asyncio.sleep(interval)
    
    def get_current_metrics(self) -> Optional[PerformanceMetrics]:
        """Get the most recent metrics"""
        return self.metrics_history[-1] if self.metrics_history else None
    
    def get_metrics_summary(self, hours: int = 1) -> Dict[str, Any]:
        """Get metrics summary for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {}
        
        # Calculate averages
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_response_time = sum(m.response_time_avg for m in recent_metrics) / len(recent_metrics)
        avg_rps = sum(m.requests_per_second for m in recent_metrics) / len(recent_metrics)
        avg_error_rate = sum(m.error_rate for m in recent_metrics) / len(recent_metrics)
        
        # Calculate peaks
        max_cpu = max(m.cpu_percent for m in recent_metrics)
        max_memory = max(m.memory_percent for m in recent_metrics)
        max_response_time = max(m.response_time_avg for m in recent_metrics)
        max_rps = max(m.requests_per_second for m in recent_metrics)
        
        return {
            "period_hours": hours,
            "sample_count": len(recent_metrics),
            "averages": {
                "cpu_percent": avg_cpu,
                "memory_percent": avg_memory,
                "response_time_ms": avg_response_time,
                "requests_per_second": avg_rps,
                "error_rate_percent": avg_error_rate,
            },
            "peaks": {
                "cpu_percent": max_cpu,
                "memory_percent": max_memory,
                "response_time_ms": max_response_time,
                "requests_per_second": max_rps,
            },
            "alerts_count": len([a for a in self.alerts if a["timestamp"] >= cutoff_time])
        }
    
    def get_alerts(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get alerts for the last N hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [a for a in self.alerts if a["timestamp"] >= cutoff_time]
    
    def export_metrics(self, hours: int = 24) -> str:
        """Export metrics to JSON string"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_metrics = [m for m in self.metrics_history if m.timestamp >= cutoff_time]
        
        # Convert to serializable format
        data = {
            "export_time": datetime.now().isoformat(),
            "period_hours": hours,
            "metrics": [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "cpu_percent": m.cpu_percent,
                    "memory_percent": m.memory_percent,
                    "memory_used_gb": m.memory_used_gb,
                    "memory_available_gb": m.memory_available_gb,
                    "response_time_avg": m.response_time_avg,
                    "requests_per_second": m.requests_per_second,
                    "error_rate": m.error_rate,
                    "cache_hit_rate": m.cache_hit_rate,
                    "database_connections": m.database_connections,
                    "database_query_time": m.database_query_time,
                }
                for m in recent_metrics
            ],
            "alerts": self.get_alerts(hours)
        }
        
        return json.dumps(data, indent=2)

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

# Middleware for request tracking
class PerformanceMiddleware:
    """Middleware to track request performance"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        start_time = time.time()
        is_error = False
        
        async def send_wrapper(message):
            nonlocal is_error
            if message["type"] == "http.response.start":
                if message["status"] >= 400:
                    is_error = True
            await send(message)
        
        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            is_error = True
            raise
        finally:
            response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            performance_monitor.record_request(response_time, is_error)

# Utility functions
def get_performance_summary() -> Dict[str, Any]:
    """Get current performance summary"""
    return performance_monitor.get_metrics_summary(1)

def get_current_alerts() -> List[Dict[str, Any]]:
    """Get current alerts"""
    return performance_monitor.get_alerts(1)

def start_performance_monitoring(interval: int = 30):
    """Start performance monitoring"""
    asyncio.create_task(performance_monitor.start_monitoring(interval))

def stop_performance_monitoring():
    """Stop performance monitoring"""
    asyncio.create_task(performance_monitor.stop_monitoring())
