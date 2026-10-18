"""
Database query analysis and slow query logging system.
Helps identify performance bottlenecks in database operations.
"""

import hashlib
import time
from typing import Any, Dict, List

from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.utils.logger import log


class QueryAnalyzer:
    """Analyzes database queries for performance optimization"""
    
    def __init__(self):
        self.slow_queries = []
        self.query_stats = {}
        self.slow_query_threshold = 100  # 100ms threshold
        self.max_slow_queries = 1000  # Keep last 1000 slow queries
        
    def setup_query_monitoring(self, engine: Engine):
        """Setup query monitoring for the database engine"""
        
        @event.listens_for(engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time"""
            context._query_start_time = time.time()
            context._query_statement = statement
            context._query_parameters = parameters
        
        @event.listens_for(engine, "after_cursor_execute")
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Analyze query performance after execution"""
            if hasattr(context, '_query_start_time'):
                execution_time = (time.time() - context._query_start_time) * 1000  # Convert to ms
                
                # Generate query fingerprint for grouping similar queries
                query_fingerprint = self._generate_query_fingerprint(statement)
                
                # Record query statistics
                self._record_query_stats(query_fingerprint, execution_time, statement, parameters)
                
                # Log slow queries
                if execution_time > self.slow_query_threshold:
                    self._log_slow_query(execution_time, statement, parameters, query_fingerprint)
    
    def _generate_query_fingerprint(self, statement: str) -> str:
        """Generate a fingerprint for the query to group similar queries"""
        # Normalize the query by removing specific values
        normalized = statement.lower()
        
        # Replace common patterns that vary but don't affect performance
        import re
        normalized = re.sub(r'\b\d+\b', '?', normalized)  # Replace numbers
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # Replace string literals
        normalized = re.sub(r'"[^"]*"', '"?"', normalized)  # Replace quoted strings
        
        # Create hash of normalized query
        return hashlib.md5(normalized.encode()).hexdigest()[:8]
    
    def _record_query_stats(self, fingerprint: str, execution_time: float, statement: str, parameters: Any):
        """Record statistics for query performance analysis"""
        if fingerprint not in self.query_stats:
            self.query_stats[fingerprint] = {
                "count": 0,
                "total_time": 0,
                "min_time": float('inf'),
                "max_time": 0,
                "avg_time": 0,
                "sample_query": statement[:200] + "..." if len(statement) > 200 else statement
            }
        
        stats = self.query_stats[fingerprint]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["max_time"] = max(stats["max_time"], execution_time)
        stats["avg_time"] = stats["total_time"] / stats["count"]
    
    def _log_slow_query(self, execution_time: float, statement: str, parameters: Any, fingerprint: str):
        """Log slow queries for analysis"""
        slow_query = {
            "timestamp": time.time(),
            "execution_time_ms": round(execution_time, 2),
            "fingerprint": fingerprint,
            "statement": statement[:500] + "..." if len(statement) > 500 else statement,
            "parameters": str(parameters)[:200] + "..." if len(str(parameters)) > 200 else str(parameters)
        }
        
        self.slow_queries.append(slow_query)
        
        # Keep only the most recent slow queries
        if len(self.slow_queries) > self.max_slow_queries:
            self.slow_queries = self.slow_queries[-self.max_slow_queries:]
        
        # Log the slow query
        log.logs.warning(f"🐌 [SLOW_QUERY] {execution_time:.2f}ms - {fingerprint}")
        log.logs.debug(f"   Query: {statement[:200]}...")
        if parameters:
            log.logs.debug(f"   Params: {parameters}")
    
    def get_query_performance_report(self) -> Dict[str, Any]:
        """Generate a performance report for all queries"""
        if not self.query_stats:
            return {"message": "No query statistics available"}
        
        # Sort queries by total time (most expensive first)
        sorted_queries = sorted(
            self.query_stats.items(),
            key=lambda x: x[1]["total_time"],
            reverse=True
        )
        
        # Calculate summary statistics
        total_queries = sum(stats["count"] for stats in self.query_stats.values())
        total_time = sum(stats["total_time"] for stats in self.query_stats.values())
        slow_query_count = len(self.slow_queries)
        
        report = {
            "summary": {
                "total_unique_queries": len(self.query_stats),
                "total_query_executions": total_queries,
                "total_execution_time_ms": round(total_time, 2),
                "average_execution_time_ms": round(total_time / total_queries, 2) if total_queries > 0 else 0,
                "slow_queries_count": slow_query_count,
                "slow_query_threshold_ms": self.slow_query_threshold
            },
            "top_queries_by_total_time": [
                {
                    "fingerprint": fingerprint,
                    "count": stats["count"],
                    "total_time_ms": round(stats["total_time"], 2),
                    "avg_time_ms": round(stats["avg_time"], 2),
                    "min_time_ms": round(stats["min_time"], 2),
                    "max_time_ms": round(stats["max_time"], 2),
                    "sample_query": stats["sample_query"]
                }
                for fingerprint, stats in sorted_queries[:10]
            ],
            "top_queries_by_frequency": [
                {
                    "fingerprint": fingerprint,
                    "count": stats["count"],
                    "avg_time_ms": round(stats["avg_time"], 2),
                    "sample_query": stats["sample_query"]
                }
                for fingerprint, stats in sorted(
                    self.query_stats.items(),
                    key=lambda x: x[1]["count"],
                    reverse=True
                )[:10]
            ]
        }
        
        return report
    
    def get_slow_queries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent slow queries"""
        return self.slow_queries[-limit:] if self.slow_queries else []
    
    def clear_stats(self):
        """Clear all query statistics"""
        self.query_stats.clear()
        self.slow_queries.clear()
        log.logs.info("🗑️ [QUERY_ANALYZER] Statistics cleared")
    
    def set_slow_query_threshold(self, threshold_ms: float):
        """Set the threshold for slow query detection"""
        self.slow_query_threshold = threshold_ms
        log.logs.info(f"⏱️ [QUERY_ANALYZER] Slow query threshold set to {threshold_ms}ms")


# Global query analyzer instance
query_analyzer = QueryAnalyzer()


def setup_database_monitoring(engine: Engine):
    """Setup database monitoring for the given engine"""
    query_analyzer.setup_query_monitoring(engine)
    log.logs.info("🔍 [QUERY_ANALYZER] Database monitoring enabled")


def get_performance_report() -> Dict[str, Any]:
    """Get current query performance report"""
    return query_analyzer.get_query_performance_report()


def get_slow_queries(limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent slow queries"""
    return query_analyzer.get_slow_queries(limit)


def clear_query_stats():
    """Clear all query statistics"""
    query_analyzer.clear_stats()


def set_slow_query_threshold(threshold_ms: float):
    """Set slow query detection threshold"""
    query_analyzer.set_slow_query_threshold(threshold_ms)
