"""
Configuration settings for CRUD optimization.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class OptimizationLevel(Enum):
    """Optimization levels for CRUD operations."""
    NONE = "none"
    BASIC = "basic"
    ADVANCED = "advanced"
    MAXIMUM = "maximum"


@dataclass
class CacheConfig:
    """Cache configuration settings."""
    enabled: bool = True
    default_ttl: int = 300  # 5 minutes
    max_cache_size: int = 1000
    enable_query_cache: bool = True
    enable_result_cache: bool = True
    cache_invalidation_enabled: bool = True


@dataclass
class QueryConfig:
    """Query optimization configuration."""
    enable_batch_processing: bool = True
    enable_query_planning: bool = True
    enable_index_hints: bool = True
    max_batch_size: int = 1000
    slow_query_threshold: float = 1.0  # seconds
    enable_query_compression: bool = True


@dataclass
class PerformanceConfig:
    """Performance monitoring configuration."""
    enable_monitoring: bool = True
    enable_slow_query_logging: bool = True
    enable_performance_metrics: bool = True
    metrics_retention_days: int = 7
    enable_auto_optimization: bool = True


@dataclass
class OptimizationConfig:
    """Main optimization configuration."""
    level: OptimizationLevel = OptimizationLevel.ADVANCED
    cache: Optional[CacheConfig] = field(default_factory=CacheConfig)
    query: Optional[QueryConfig] = field(default_factory=QueryConfig)
    performance: Optional[PerformanceConfig] = field(default_factory=PerformanceConfig)


# Default configurations for different environments
DEVELOPMENT_CONFIG = OptimizationConfig(
    level=OptimizationLevel.BASIC,
    cache=CacheConfig(
        enabled=True,
        default_ttl=60,  # 1 minute for development
        max_cache_size=100
    ),
    query=QueryConfig(
        enable_batch_processing=True,
        slow_query_threshold=0.5
    ),
    performance=PerformanceConfig(
        enable_monitoring=True,
        enable_slow_query_logging=True
    )
)

PRODUCTION_CONFIG = OptimizationConfig(
    level=OptimizationLevel.MAXIMUM,
    cache=CacheConfig(
        enabled=True,
        default_ttl=600,  # 10 minutes for production
        max_cache_size=5000
    ),
    query=QueryConfig(
        enable_batch_processing=True,
        enable_query_planning=True,
        enable_index_hints=True,
        max_batch_size=2000,
        slow_query_threshold=2.0
    ),
    performance=PerformanceConfig(
        enable_monitoring=True,
        enable_slow_query_logging=True,
        enable_performance_metrics=True,
        metrics_retention_days=30,
        enable_auto_optimization=True
    )
)

TESTING_CONFIG = OptimizationConfig(
    level=OptimizationLevel.NONE,
    cache=CacheConfig(
        enabled=False
    ),
    query=QueryConfig(
        enable_batch_processing=False,
        slow_query_threshold=0.1
    ),
    performance=PerformanceConfig(
        enable_monitoring=False,
        enable_slow_query_logging=False
    )
)


class OptimizationManager:
    """
    Manages optimization configuration and settings.
    """
    
    def __init__(self, config: Optional[OptimizationConfig] = None):
        self.config = config or PRODUCTION_CONFIG
        self._model_configs: Dict[str, OptimizationConfig] = {}
    
    def get_config(self) -> OptimizationConfig:
        """Get the current optimization configuration."""
        return self.config
    
    def set_config(self, config: OptimizationConfig):
        """Set the optimization configuration."""
        self.config = config
    
    def set_model_config(self, model_name: str, config: OptimizationConfig):
        """Set optimization configuration for a specific model."""
        self._model_configs[model_name] = config
    
    def get_model_config(self, model_name: str) -> OptimizationConfig:
        """Get optimization configuration for a specific model."""
        return self._model_configs.get(model_name, self.config)
    
    def is_optimization_enabled(self, model_name: Optional[str] = None) -> bool:
        """Check if optimization is enabled."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.level != OptimizationLevel.NONE
    
    def is_caching_enabled(self, model_name: Optional[str] = None) -> bool:
        """Check if caching is enabled."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.cache is not None and config.cache.enabled and config.level != OptimizationLevel.NONE
    
    def get_cache_ttl(self, model_name: Optional[str] = None) -> int:
        """Get cache TTL for a model."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.cache.default_ttl if config.cache is not None else 300
    
    def is_batch_processing_enabled(self, model_name: Optional[str] = None) -> bool:
        """Check if batch processing is enabled."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.query.enable_batch_processing if config.query is not None else True
    
    def get_max_batch_size(self, model_name: Optional[str] = None) -> int:
        """Get maximum batch size for a model."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.query.max_batch_size if config.query is not None else 1000
    
    def get_slow_query_threshold(self, model_name: Optional[str] = None) -> float:
        """Get slow query threshold for a model."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.query.slow_query_threshold if config.query is not None else 1.0
    
    def is_monitoring_enabled(self, model_name: Optional[str] = None) -> bool:
        """Check if performance monitoring is enabled."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.performance.enable_monitoring if config.performance is not None else True
    
    def get_optimization_level(self, model_name: Optional[str] = None) -> OptimizationLevel:
        """Get optimization level for a model."""
        config = self.get_model_config(model_name) if model_name else self.config
        return config.level
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values."""
        if 'level' in updates:
            self.config.level = OptimizationLevel(updates['level'])
        
        if 'cache' in updates:
            cache_updates = updates['cache']
            for key, value in cache_updates.items():
                if hasattr(self.config.cache, key):
                    setattr(self.config.cache, key, value)
        
        if 'query' in updates:
            query_updates = updates['query']
            for key, value in query_updates.items():
                if hasattr(self.config.query, key):
                    setattr(self.config.query, key, value)
        
        if 'performance' in updates:
            performance_updates = updates['performance']
            for key, value in performance_updates.items():
                if hasattr(self.config.performance, key):
                    setattr(self.config.performance, key, value)
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration."""
        return {
            'level': self.config.level.value,
            'cache': {
                'enabled': self.config.cache.enabled if self.config.cache else False,
                'default_ttl': self.config.cache.default_ttl if self.config.cache else 300,
                'max_cache_size': self.config.cache.max_cache_size if self.config.cache else 1000
            },
            'query': {
                'batch_processing': self.config.query.enable_batch_processing if self.config.query else True,
                'max_batch_size': self.config.query.max_batch_size if self.config.query else 1000,
                'slow_query_threshold': self.config.query.slow_query_threshold if self.config.query else 1.0
            },
            'performance': {
                'monitoring': self.config.performance.enable_monitoring if self.config.performance else True,
                'slow_query_logging': self.config.performance.enable_slow_query_logging if self.config.performance else True,
                'auto_optimization': self.config.performance.enable_auto_optimization if self.config.performance else True
            }
        }


# Global optimization manager instance
optimization_manager = OptimizationManager()


def get_optimization_config(model_name: Optional[str] = None) -> OptimizationConfig:
    """Get optimization configuration for a model."""
    return optimization_manager.get_model_config(model_name) if model_name else optimization_manager.get_config()


def is_optimization_enabled(model_name: Optional[str] = None) -> bool:
    """Check if optimization is enabled for a model."""
    return optimization_manager.is_optimization_enabled(model_name)


def is_caching_enabled(model_name: Optional[str] = None) -> bool:
    """Check if caching is enabled for a model."""
    return optimization_manager.is_caching_enabled(model_name)


def get_cache_ttl(model_name: Optional[str] = None) -> int:
    """Get cache TTL for a model."""
    return optimization_manager.get_cache_ttl(model_name)
