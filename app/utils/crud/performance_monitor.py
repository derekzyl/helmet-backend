"""
Performance monitoring and optimization utilities for CRUD operations.
"""

import asyncio
import statistics
import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List

from app.utils.logger import log


class PerformanceMonitor:
    """
    Monitor and track performance metrics for database operations.
    """
    
    def __init__(self):
        self.metrics = {
            'query_times': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'slow_queries': [],
            'error_count': 0,
            'total_queries': 0
        }
        self.slow_query_threshold = 1.0  # seconds
        self.max_metrics_history = 1000
    
    def record_query_time(self, query_time: float, query_info: Dict[str, Any]):
        """Record query execution time and metadata."""
        self.metrics['query_times'].append(query_time)
        self.metrics['total_queries'] += 1
        
        # Keep only recent metrics
        if len(self.metrics['query_times']) > self.max_metrics_history:
            self.metrics['query_times'] = self.metrics['query_times'][-self.max_metrics_history:]
        
        # Track slow queries
        if query_time > self.slow_query_threshold:
            self.metrics['slow_queries'].append({
                'time': query_time,
                'info': query_info,
                'timestamp': datetime.now()
            })
            
            # Keep only recent slow queries
            if len(self.metrics['slow_queries']) > 100:
                self.metrics['slow_queries'] = self.metrics['slow_queries'][-100:]
    
    def record_cache_hit(self):
        """Record a cache hit."""
        self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """Record a cache miss."""
        self.metrics['cache_misses'] += 1
    
    def record_error(self):
        """Record an error."""
        self.metrics['error_count'] += 1
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get current performance statistics."""
        if not self.metrics['query_times']:
            return {
                'total_queries': 0,
                'average_query_time': 0,
                'median_query_time': 0,
                'p95_query_time': 0,
                'p99_query_time': 0,
                'cache_hit_rate': 0,
                'slow_query_count': 0,
                'error_rate': 0
            }
        
        query_times = self.metrics['query_times']
        total_queries = self.metrics['total_queries']
        cache_hits = self.metrics['cache_hits']
        cache_misses = self.metrics['cache_misses']
        total_cache_requests = cache_hits + cache_misses
        
        return {
            'total_queries': total_queries,
            'average_query_time': statistics.mean(query_times),
            'median_query_time': statistics.median(query_times),
            'p95_query_time': self._percentile(query_times, 95),
            'p99_query_time': self._percentile(query_times, 99),
            'cache_hit_rate': (cache_hits / total_cache_requests * 100) if total_cache_requests > 0 else 0,
            'slow_query_count': len(self.metrics['slow_queries']),
            'error_rate': (self.metrics['error_count'] / total_queries * 100) if total_queries > 0 else 0
        }
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]
    
    def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent slow queries."""
        return sorted(
            self.metrics['slow_queries'], 
            key=lambda x: x['time'], 
            reverse=True
        )[:limit]
    
    def reset_metrics(self):
        """Reset all performance metrics."""
        self.metrics = {
            'query_times': [],
            'cache_hits': 0,
            'cache_misses': 0,
            'slow_queries': [],
            'error_count': 0,
            'total_queries': 0
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def monitor_performance(operation_name: str = "database_operation"):
    """
    Decorator to monitor performance of database operations.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            query_info = {
                'operation': operation_name,
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            }
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                performance_monitor.record_query_time(execution_time, query_info)
                
                if execution_time > performance_monitor.slow_query_threshold:
                    log.logs.warning(f"Slow query detected: {operation_name} took {execution_time:.2f}s")
                
                return result
            except Exception:
                performance_monitor.record_error()
                execution_time = time.time() - start_time
                performance_monitor.record_query_time(execution_time, query_info)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            query_info = {
                'operation': operation_name,
                'function': func.__name__,
                'args_count': len(args),
                'kwargs_count': len(kwargs)
            }
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                performance_monitor.record_query_time(execution_time, query_info)
                
                if execution_time > performance_monitor.slow_query_threshold:
                    log.logs.warning(f"Slow query detected: {operation_name} took {execution_time:.2f}s")
                
                return result
            except Exception:
                performance_monitor.record_error()
                execution_time = time.time() - start_time
                performance_monitor.record_query_time(execution_time, query_info)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


class QueryOptimizer:
    """
    Query optimization utilities and suggestions.
    """
    
    @staticmethod
    def analyze_query_performance(query_info: Dict[str, Any]) -> List[str]:
        """Analyze query performance and return optimization suggestions."""
        suggestions = []
        
        # Check for common performance issues
        if query_info.get('has_joins', False) and not query_info.get('has_indexes', False):
            suggestions.append("Consider adding indexes on join columns")
        
        if query_info.get('select_all_fields', False):
            suggestions.append("Consider selecting only required fields to reduce data transfer")
        
        if query_info.get('no_pagination', False):
            suggestions.append("Consider adding pagination for large result sets")
        
        if query_info.get('complex_filters', False):
            suggestions.append("Consider optimizing filter conditions or adding composite indexes")
        
        if query_info.get('n_plus_one_queries', False):
            suggestions.append("Consider using eager loading to avoid N+1 query problems")
        
        return suggestions
    
    @staticmethod
    def suggest_indexes(model_class, common_filters: List[str]) -> List[str]:
        """Suggest database indexes based on common filter patterns."""
        suggestions = []
        
        # Single column indexes
        for filter_field in common_filters:
            if hasattr(model_class, filter_field):
                suggestions.append(f"CREATE INDEX idx_{model_class.__tablename__}_{filter_field} ON {model_class.__tablename__} ({filter_field});")
        
        # Composite indexes for common filter combinations
        if len(common_filters) > 1:
            filter_combo = "_".join(common_filters[:3])  # Limit to 3 columns
            suggestions.append(f"CREATE INDEX idx_{model_class.__tablename__}_{filter_combo} ON {model_class.__tablename__} ({', '.join(common_filters[:3])});")
        
        return suggestions


def get_performance_report() -> Dict[str, Any]:
    """Get a comprehensive performance report."""
    stats = performance_monitor.get_performance_stats()
    slow_queries = performance_monitor.get_slow_queries(5)
    
    return {
        'performance_stats': stats,
        'slow_queries': slow_queries,
        'recommendations': _generate_recommendations(stats)
    }


def _generate_recommendations(stats: Dict[str, Any]) -> List[str]:
    """Generate performance recommendations based on stats."""
    recommendations = []
    
    if stats['average_query_time'] > 0.5:
        recommendations.append("Average query time is high. Consider adding database indexes or optimizing queries.")
    
    if stats['cache_hit_rate'] < 70:
        recommendations.append("Cache hit rate is low. Consider increasing cache TTL or improving cache keys.")
    
    if stats['slow_query_count'] > 10:
        recommendations.append("Many slow queries detected. Review and optimize slow query patterns.")
    
    if stats['error_rate'] > 5:
        recommendations.append("High error rate detected. Review error logs and fix underlying issues.")
    
    return recommendations
