"""
Usage examples for the optimized CRUD service.
This file demonstrates how to use the new optimized CRUD operations.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.crud.migration_helper import (
    HybridCrudService,
    get_optimized_crud_service,
)
from app.utils.crud.optimization_config import PRODUCTION_CONFIG, optimization_manager
from app.utils.crud.optimized_service_crud import OptimizedCrudService
from app.utils.crud.performance_monitor import (
    get_performance_report,
    monitor_performance,
)


# Example 1: Basic usage with optimized CRUD service
async def example_basic_usage(db: AsyncSession, model_class):
    """Basic usage example."""
    
    # Create optimized CRUD service
    crud_service = OptimizedCrudService(model_class, db, current_user_id="user123")
    
    # Get many records with caching
    result = await crud_service.get_many(
        query={"page": 1, "limit": 10, "sort": "-created_at"},
        filter={"is_active": True},
        select_fields=["id", "name", "created_at"]
    )
    
    print(f"Found {result['doc_length']} records")
    return result


# Example 2: Using hybrid service with fallback
async def example_hybrid_usage(db: AsyncSession, model_class):
    """Hybrid service example with automatic fallback."""
    
    # Create hybrid service
    crud_service = HybridCrudService(
        model_class, 
        db, 
        current_user_id="user123",
        use_optimized=True,
        fallback_to_old=True
    )
    
    # This will use optimized service, but fallback to old if it fails
    result = await crud_service.get_many(
        query={"page": 1, "limit": 50},
        populate=[
            {"path": "related_model", "fields": ["id", "name"]},
            {"path": "nested_model", "fields": ["id", "title"]}
        ]
    )
    
    # Check usage statistics
    stats = crud_service.get_usage_stats()
    print(f"Optimized calls: {stats['optimized_calls']}")
    print(f"Fallback calls: {stats['fallback_calls']}")
    
    return result


# Example 3: Performance monitoring
@monitor_performance("bulk_operations")
async def example_bulk_operations(db: AsyncSession, model_class):
    """Example with performance monitoring."""
    
    crud_service = get_optimized_crud_service(model_class, db, "user123")
    
    # Bulk create with monitoring
    bulk_data = [
        {"name": f"Item {i}", "description": f"Description {i}"}
        for i in range(100)
    ]
    
    result = await crud_service.create_many(
        data=bulk_data,
        batch_size=50
    )
    
    print(f"Created {result['doc_length']} records")
    return result


# Example 4: Advanced querying with MongoDB-style operators
async def example_advanced_querying(db: AsyncSession, model_class):
    """Advanced querying example."""
    
    crud_service = OptimizedCrudService(model_class, db, "user123")
    
    # Complex query with MongoDB operators
    result = await crud_service.get_many(
        query={
            "page": 1,
            "limit": 20,
            "sort": "-created_at",
            # MongoDB-style operators
            "age": {"$gte": 18, "$lt": 65},
            "status": {"$in": ["active", "pending"]},
            "name": {"$regex": "john"},
            "$or": [
                {"category": "premium"},
                {"priority": {"$gt": 5}}
            ]
        }
    )
    
    return result


# Example 5: Configuration management
async def example_configuration_management():
    """Configuration management example."""
    
    # Set production configuration
    optimization_manager.set_config(PRODUCTION_CONFIG)
    
    # Get current configuration
    config_summary = optimization_manager.get_config_summary()
    print("Current configuration:", config_summary)
    
    # Update specific settings
    optimization_manager.update_config({
        'cache': {
            'default_ttl': 900,  # 15 minutes
            'max_cache_size': 2000
        },
        'query': {
            'slow_query_threshold': 1.5
        }
    })
    
    # Check if optimization is enabled for a specific model
    is_enabled = optimization_manager.is_optimization_enabled("UserModel")
    print(f"Optimization enabled for UserModel: {is_enabled}")


# Example 6: Performance reporting
async def example_performance_reporting():
    """Performance reporting example."""
    
    # Get comprehensive performance report
    report = get_performance_report()
    
    print("Performance Statistics:")
    stats = report['performance_stats']
    print(f"  Total queries: {stats['total_queries']}")
    print(f"  Average query time: {stats['average_query_time']:.3f}s")
    print(f"  Cache hit rate: {stats['cache_hit_rate']:.1f}%")
    print(f"  Slow queries: {stats['slow_query_count']}")
    
    print("\nSlow Queries:")
    for slow_query in report['slow_queries']:
        print(f"  - {slow_query['time']:.3f}s: {slow_query['info']}")
    
    print("\nRecommendations:")
    for recommendation in report['recommendations']:
        print(f"  - {recommendation}")


# Example 7: Migration from old to optimized service
async def example_migration(db: AsyncSession, model_class):
    """Migration example."""
    
    # Start with old service
    from app.utils.crud.service_crud import CrudService
    old_service = CrudService(model_class, db, "user123")
    
    # Test with old service
    old_result = await old_service.get_many(
        query={"page": 1, "limit": 10}
    )
    print(f"Old service result: {old_result['doc_length']} records")
    
    # Migrate to optimized service
    from app.utils.crud.migration_helper import migrate_to_optimized
    optimized_service = migrate_to_optimized(old_service, db)
    
    # Test with optimized service
    optimized_result = await optimized_service.get_many(
        query={"page": 1, "limit": 10}
    )
    print(f"Optimized service result: {optimized_result['doc_length']} records")
    
    return optimized_result


# Example 8: Model-specific configuration
async def example_model_specific_config():
    """Model-specific configuration example."""
    
    # Set different configurations for different models
    from app.utils.crud.optimization_config import (
        CacheConfig,
        OptimizationConfig,
        QueryConfig,
    )
    
    # High-performance config for critical models
    critical_config = OptimizationConfig(
        cache=CacheConfig(default_ttl=1800, max_cache_size=5000),  # 30 minutes
        query=QueryConfig(max_batch_size=2000, slow_query_threshold=0.5)
    )
    
    # Standard config for regular models
    standard_config = OptimizationConfig(
        cache=CacheConfig(default_ttl=300, max_cache_size=1000),  # 5 minutes
        query=QueryConfig(max_batch_size=1000, slow_query_threshold=1.0)
    )
    
    # Apply configurations
    optimization_manager.set_model_config("UserModel", critical_config)
    optimization_manager.set_model_config("ProductModel", standard_config)
    
    # Check configurations
    user_config = optimization_manager.get_model_config("UserModel")
    product_config = optimization_manager.get_model_config("ProductModel")
    
    print(f"User model config: {user_config}")
    print(f"Product model config: {product_config}")

# Example 9: Error handling and fallback
async def example_error_handling(db: AsyncSession, model_class):
    """Error handling example."""
    
    crud_service = HybridCrudService(
        model_class, 
        db, 
        current_user_id="user123",
        use_optimized=True,
        fallback_to_old=True
    )
    
    try:
        # This might fail with optimized service
        result = await crud_service.get_many(
            query={"page": 1, "limit": 10},
            use_optimized=True  # Force optimized service
        )
        print("Optimized service succeeded")
        return result
        
    except Exception as e:
        print(f"Optimized service failed: {e}")
        
        # Fallback to old service
        result = await crud_service.get_many(
            query={"page": 1, "limit": 10},
            use_optimized=False  # Force old service
        )
        print("Fallback to old service succeeded")
        return result


# Example 10: Complete workflow
async def example_complete_workflow(db: AsyncSession, model_class):
    """Complete workflow example."""
    
    # 1. Configure optimization
    optimization_manager.set_config(PRODUCTION_CONFIG)
    
    # 2. Create optimized service
    crud_service = get_optimized_crud_service(model_class, db, "user123")
    
    # 3. Create some data
    create_result = await crud_service.create({
        "name": "Test Item",
        "description": "Test Description",
        "is_active": True
    })
    print(f"Created item: {create_result['data']['id']}")
    
    # 4. Query with caching
    query_result = await crud_service.get_many(
        query={"page": 1, "limit": 10, "sort": "-created_at"},
        filter={"is_active": True}
    )
    print(f"Found {query_result['doc_length']} active items")
    
    # 5. Update with cache invalidation
    update_result = await crud_service.update(
        filter={"id": create_result['data']['id']},
        data={"description": "Updated Description"}
    )
    print(f"Updated {update_result['doc_length']} items")
    
    # 6. Get performance report
    report = get_performance_report()
    print(f"Performance: {report['performance_stats']['total_queries']} queries executed")
    
    return {
        "created": create_result,
        "queried": query_result,
        "updated": update_result,
        "performance": report
    }
