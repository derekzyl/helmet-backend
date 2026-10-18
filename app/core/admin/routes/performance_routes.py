"""
Performance monitoring and analysis routes.
Provides endpoints for viewing database performance metrics and slow queries.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from app.config.database.optimized_pool import optimized_pool
from app.core.auth.services.service_auth import get_current_user
from app.core.users.models.model_user import UserModel
from app.utils.database.query_analyzer import (
    clear_query_stats,
    get_performance_report,
    get_slow_queries,
    set_slow_query_threshold,
)
from app.utils.logger import log

router = APIRouter(prefix="/admin/performance", tags=["Performance Monitoring"])


@router.get("/query-report")
async def get_query_performance_report(
    current_user: UserModel = Depends(get_current_user)
) -> JSONResponse:
    """
    Get database query performance report.
    Shows statistics about query execution times, slow queries, and performance bottlenecks.
    """
    try:
        # Check if user has admin permissions
        if not hasattr(current_user, 'is_admin'):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        report = get_performance_report()
        
        log.logs.info(f"📊 [PERF] Query performance report requested by {current_user.id}")
        
        return JSONResponse(content={
            "success": True,
            "data": report,
            "message": "Query performance report generated successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        log.logs.error(f"❌ [PERF] Error generating query report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate performance report")


@router.get("/slow-queries")
async def get_slow_queries_list(
    limit: int = 50,
    current_user: UserModel = Depends(get_current_user)
) -> JSONResponse:
    """
    Get list of recent slow queries.
    
    Args:
        limit: Maximum number of slow queries to return (default: 50)
    """
    try:
        # Check if user has admin permissions
        if not hasattr(current_user, 'is_admin') :
            raise HTTPException(status_code=403, detail="Admin access required")
        
        slow_queries = get_slow_queries(limit)
        
        log.logs.info(f"🐌 [PERF] Slow queries list requested by {current_user.id} (limit: {limit})")
        
        return JSONResponse(content={
            "success": True,
            "data": {
                "slow_queries": slow_queries,
                "count": len(slow_queries),
                "limit": limit
            },
            "message": f"Retrieved {len(slow_queries)} slow queries"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        log.logs.error(f"❌ [PERF] Error retrieving slow queries: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve slow queries")


@router.get("/pool-status")
async def get_database_pool_status(
    current_user: UserModel = Depends(get_current_user)
) -> JSONResponse:
    """
    Get current database connection pool status.
    Shows pool utilization, connection counts, and performance metrics.
    """
    try:
        # Check if user has admin permissions
        if not hasattr(current_user, 'is_admin') :
            raise HTTPException(status_code=403, detail="Admin access required")
        
        pool_status = optimized_pool.get_pool_status()
        
        log.logs.info(f"🔗 [PERF] Pool status requested by {current_user.id}")
        
        return JSONResponse(content={
            "success": True,
            "data": pool_status,
            "message": "Database pool status retrieved successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        log.logs.error(f"❌ [PERF] Error retrieving pool status: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve pool status")


@router.post("/clear-stats")
async def clear_performance_stats(
    current_user: UserModel = Depends(get_current_user)
) -> JSONResponse:
    """
    Clear all query performance statistics.
    This will reset the performance monitoring data.
    """
    try:
        # Check if user has admin permissions
        if not hasattr(current_user, 'is_admin') :
            raise HTTPException(status_code=403, detail="Admin access required")
        
        clear_query_stats()
        
        log.logs.info(f"🗑️ [PERF] Performance stats cleared by {current_user.id}")
        
        return JSONResponse(content={
            "success": True,
            "message": "Performance statistics cleared successfully"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        log.logs.error(f"❌ [PERF] Error clearing performance stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear performance statistics")


@router.post("/set-threshold")
async def set_slow_query_threshold_endpoint(
    threshold_ms: float,
    current_user: UserModel = Depends(get_current_user)
) -> JSONResponse:
    """
    Set the threshold for slow query detection.
    
    Args:
        threshold_ms: Threshold in milliseconds for slow query detection
    """
    try:
        # Check if user has admin permissions
        if not hasattr(current_user, 'is_admin') :
            raise HTTPException(status_code=403, detail="Admin access required")
        
        if threshold_ms < 0:
            raise HTTPException(status_code=400, detail="Threshold must be positive")
        
        set_slow_query_threshold(threshold_ms)
        
        log.logs.info(f"⏱️ [PERF] Slow query threshold set to {threshold_ms}ms by {current_user.id}")
        
        return JSONResponse(content={
            "success": True,
            "message": f"Slow query threshold set to {threshold_ms}ms"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        log.logs.error(f"❌ [PERF] Error setting slow query threshold: {e}")
        raise HTTPException(status_code=500, detail="Failed to set slow query threshold")


@router.get("/health")
async def performance_health_check(
    current_user: UserModel = Depends(get_current_user)
) -> JSONResponse:
    """
    Perform a comprehensive performance health check.
    Checks database connectivity, pool status, and recent performance metrics.
    """
    try:
        # Check if user has admin permissions
        if not hasattr(current_user, 'is_admin') :
            raise HTTPException(status_code=403, detail="Admin access required")
        
        # Perform database health check
        db_healthy = await optimized_pool.health_check()
        
        # Get pool status
        pool_status = optimized_pool.get_pool_status()
        
        # Get recent slow queries count
        recent_slow_queries = get_slow_queries(10)
        
        health_status = {
            "database_healthy": db_healthy,
            "pool_status": pool_status,
            "recent_slow_queries_count": len(recent_slow_queries),
            "performance_monitoring_active": True
        }
        
        overall_healthy = db_healthy and pool_status.get("utilization_percentage", 0) < 90
        
        log.logs.info(f"🏥 [PERF] Health check performed by {current_user.id} - Healthy: {overall_healthy}")
        
        return JSONResponse(content={
            "success": True,
            "data": health_status,
            "healthy": overall_healthy,
            "message": "Performance health check completed"
        })
        
    except HTTPException:
        raise
    except Exception as e:
        log.logs.error(f"❌ [PERF] Error performing health check: {e}")
        raise HTTPException(status_code=500, detail="Failed to perform health check")
