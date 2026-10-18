"""
Migration helper to transition from old CRUD service to optimized CRUD service.
This ensures backward compatibility while providing performance improvements.
"""

from typing import Any, Dict, List, Optional, Type, Union

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config.env import env
from app.utils.crud.optimized_service_crud import OptimizedCrudService
from app.utils.crud.service_crud import CrudService, PopulateField
from app.utils.crud.super_optimised_service import UltraOptimizedCrudService
from app.utils.crud.types_crud import ResponseMessage
from app.utils.logger import log

ENABLE_PERF_LOGS = env.get("enable_perf_logs", False)  # Set to False in production


class HybridCrudService:
    """
    Hybrid CRUD service that can use either the old or optimized implementation
    based on configuration or performance requirements.
    """
    
    def __init__(
        self,
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None,
        use_optimized: bool = False,
        use_ultra_optimized: bool = True,
        fallback_to_old: bool = True
    ):
        self.model = model
        self.db = db
        self.current_user_id = current_user_id
        self.use_optimized = use_optimized
        self.fallback_to_old = fallback_to_old
        self.use_ultra_optimized = use_ultra_optimized
        # Initialize both services
        self.optimized_service = OptimizedCrudService(model, db, current_user_id)
        self.ultra_optimized_service = UltraOptimizedCrudService(model, db, current_user_id)
        self.old_service = CrudService(model, db, current_user_id)
        
        # Performance tracking
        self.optimized_calls = 0
        self.ultra_optimized_calls = 0
        self.old_calls = 0
        self.fallback_calls = 0
    
    def set_current_user(self, user_id: str):
        """Set the current user ID for audit fields"""
        self.current_user_id = user_id
        self.optimized_service.set_current_user(user_id)
        self.ultra_optimized_service.set_current_user(user_id)
        self.old_service.set_current_user(user_id)
    
    def _get_service(self, force_optimized: bool = False, force_ultra_optimized: bool = False) -> Union[OptimizedCrudService, UltraOptimizedCrudService, CrudService]:
        """Get the appropriate service based on configuration."""
        if force_ultra_optimized or self.use_ultra_optimized:
            if ENABLE_PERF_LOGS:
                log.logs.info(f"Using ultra optimized service for {self.model.__name__}")
            return self.ultra_optimized_service
        elif force_optimized or self.use_optimized:
            if ENABLE_PERF_LOGS:
                log.logs.info(f"Using optimized service for {self.model.__name__}")
            return self.optimized_service
        else:
            if ENABLE_PERF_LOGS:
                log.logs.info(f"Using old service for {self.model.__name__}")
            return self.old_service
    
    async def get_many(
        self,
        query: Dict[str, Any],
        filter: Optional[Dict[str, Any]] = None,
        select_fields: Optional[List[str]] = None,
        populate: Optional[List[PopulateField]] = None,
        use_optimized: bool|None = None,
        use_ultra_optimized: bool|None = None
    ) -> ResponseMessage:
        """Get many records with optional optimization."""
        service = self._get_service(use_optimized if use_optimized is not None else True, use_ultra_optimized if use_ultra_optimized is not None else True)
        
        try:
            if isinstance(service, OptimizedCrudService):
                self.optimized_calls += 1
            elif isinstance(service, UltraOptimizedCrudService):
                self.ultra_optimized_calls += 1
            else:
                self.old_calls += 1
            
            return await service.get_many(query, filter, select_fields, populate)
            
        except Exception as e:
            if self.fallback_to_old and isinstance(service, OptimizedCrudService):
                log.logs.warning(f"Optimized service failed, falling back to old service: {e}")
                self.fallback_calls += 1
                return await self.old_service.get_many(query, filter, select_fields, populate)
            else:
                raise
    
    async def get_one(
        self,
        data: Dict[str, Any],
        select: Optional[List[str]] = None,
        populate: Optional[List[PopulateField]] = None,
        use_optimized: bool|None = None,
        use_ultra_optimized: bool|None = None
    ) -> ResponseMessage:
        """Get one record with optional optimization."""
        service = self._get_service(use_optimized if use_optimized is not None else True, use_ultra_optimized if use_ultra_optimized is not None else True)
        
        try:
            if isinstance(service, OptimizedCrudService):
                self.optimized_calls += 1
            elif isinstance(service, UltraOptimizedCrudService):
                self.ultra_optimized_calls += 1
            else:
                self.old_calls += 1
            
            return await service.get_one(data, select, populate)
            
        except Exception as e:
            if self.fallback_to_old and isinstance(service, OptimizedCrudService):
                log.logs.warning(f"Optimized service failed, falling back to old service: {e}")
                self.fallback_calls += 1
                return await self.old_service.get_one(data, select, populate)
            else:
                raise
    
    async def create(
        self,
        data: Dict[str, Any],
        check: Optional[Dict[str, Any]] = None,
        select: Optional[List[str]] = None,
        use_optimized: bool|None = None,
        use_ultra_optimized: bool|None = None
    ) -> ResponseMessage:
        """Create a record with optional optimization."""
        service = self._get_service(use_optimized if use_optimized is not None else True, use_ultra_optimized if use_ultra_optimized is not None else True)
        
        try:
            if isinstance(service, OptimizedCrudService):
                self.optimized_calls += 1
            elif isinstance(service, UltraOptimizedCrudService):
                self.ultra_optimized_calls += 1
            else:
                self.old_calls += 1
            
            return await service.create(data, check, select)
            
        except Exception as e:
            if self.fallback_to_old and isinstance(service, OptimizedCrudService):
                log.logs.warning(f"Optimized service failed, falling back to old service: {e}")
                self.fallback_calls += 1
                return await self.old_service.create(data, check, select)
            else:
                raise
    
    async def update(
        self,
        filter: Dict[str, Any],
        data: Dict[str, Any],
        use_optimized: Optional[bool] = None
    ) -> ResponseMessage:
        """Update records with optional optimization."""
        service = self._get_service(use_optimized if use_optimized is not None else True)
        
        try:
            if isinstance(service, OptimizedCrudService):
                self.optimized_calls += 1
            else:
                self.old_calls += 1
            
            return await service.update(filter, data)
            
        except Exception as e:
            if self.fallback_to_old and isinstance(service, OptimizedCrudService):
                log.logs.warning(f"Optimized service failed, falling back to old service: {e}")
                self.fallback_calls += 1
                return await self.old_service.update(filter, data)
            else:
                raise
    
    async def delete(
        self,
        filter: Dict[str, Any],
        use_optimized: Optional[bool] = None,
        use_ultra_optimized: Optional[bool] = None
    ) -> ResponseMessage:
        """Delete records with optional optimization."""
        service = self._get_service(use_optimized if use_optimized is not None else True, use_ultra_optimized if use_ultra_optimized is not None else True)
        
        try:
            if isinstance(service, OptimizedCrudService):
                self.optimized_calls += 1
            elif isinstance(service, UltraOptimizedCrudService):
                self.ultra_optimized_calls += 1
            else:
                self.old_calls += 1
            
            return await service.delete(filter)
            
        except Exception as e:
            if self.fallback_to_old and isinstance(service, OptimizedCrudService):
                log.logs.warning(f"Optimized service failed, falling back to old service: {e}")
                self.fallback_calls += 1
                return await self.old_service.delete(filter)
            else:
                raise
    
    async def create_many(
        self,
        data: List[Dict[str, Any]],
        check: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 1000,
        use_optimized: Optional[bool] = None,
        use_ultra_optimized: Optional[bool] = None
    ) -> ResponseMessage:
        """Create many records with optional optimization."""
        service = self._get_service(use_optimized if use_optimized is not None else True, use_ultra_optimized if use_ultra_optimized is not None else True)
        
        try:
            if isinstance(service, OptimizedCrudService):
                self.optimized_calls += 1
            elif isinstance(service, UltraOptimizedCrudService):
                self.ultra_optimized_calls += 1
            else:
                self.old_calls += 1
            
            return await service.create_many(data, check, batch_size)
            
        except Exception as e:
            if self.fallback_to_old and isinstance(service, OptimizedCrudService):
                log.logs.warning(f"Optimized service failed, falling back to old service: {e}")
                self.fallback_calls += 1
                return await self.old_service.create_many(data, check, batch_size)
            else:
                raise
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for both services."""
        total_calls = self.optimized_calls + self.ultra_optimized_calls + self.old_calls + self.fallback_calls
        
        return {
            'optimized_calls': self.optimized_calls,
            'ultra_optimized_calls': self.ultra_optimized_calls,
            'old_calls': self.old_calls,
            'fallback_calls': self.fallback_calls,
            'total_calls': total_calls,
            'optimized_usage_percentage': (self.optimized_calls / total_calls * 100) if total_calls > 0 else 0,
            'fallback_rate': (self.fallback_calls / self.optimized_calls * 100) if self.optimized_calls > 0 else 0
        }

    def get_available_relationships(self) -> List[str]:
        """Helper method to get all available relationship names on the model."""
        relationships = []
        for attr_name in dir(self.model):
            attr = getattr(self.model, attr_name)
            if (
                hasattr(attr, "property")
                and hasattr(attr.property, "mapper")
                and not attr_name.startswith("_")
            ):
                relationships.append(attr_name)
        return relationships

    def debug_populate_paths(self, populate: List[PopulateField]) -> None:
        """Debug helper to check populate paths against available relationships."""
        available_rels = self.get_available_relationships()
        log.logs.info(
            f"Available relationships in {self.model.__name__}: {available_rels}"
        )

        for pop_config in populate:
            path = pop_config.get("path")
            if path:
                if path in available_rels:
                    log.logs.info(f"✓ Populate path '{path}' is a valid relationship")
                else:
                    log.logs.warning(
                        f"✗ Populate path '{path}' is NOT a valid relationship"
                    )
                    log.logs.warning(f"  Available relationships: {available_rels}")
    def switch_to_optimized(self):
        """Switch to using optimized service by default."""
        self.use_optimized = True
        log.logs.info("Switched to optimized CRUD service")
    
    def switch_to_old(self):
        """Switch to using old service by default."""
        self.use_optimized = False
        log.logs.info("Switched to old CRUD service")


class CrudServiceFactory:
    """
    Factory class to create CRUD services with different configurations.
    """
    
    @staticmethod
    def create_optimized(
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None
    ) -> OptimizedCrudService:
        """Create an optimized CRUD service."""
        return OptimizedCrudService(model, db, current_user_id)
    

    @staticmethod
    def create_ultra_optimized(
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None
    ) -> UltraOptimizedCrudService:
        """Create an ultra optimized CRUD service."""
        return UltraOptimizedCrudService(model, db, current_user_id)
    
    @staticmethod
    def create_old(
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None
    ) -> CrudService:
        """Create the old CRUD service."""
        return CrudService(model, db, current_user_id)
    
    @staticmethod
    def create_hybrid(
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None,
        use_optimized: bool = True,
        fallback_to_old: bool = True
    ) -> HybridCrudService:
        """Create a hybrid CRUD service."""
        return HybridCrudService(model, db, current_user_id, use_optimized, fallback_to_old)
    
    @staticmethod
    def create_auto(
        model: Type[DeclarativeBase],
        db: AsyncSession,
        current_user_id: Optional[str] = None,
        auto_optimize: bool = True
    ) -> Union[OptimizedCrudService, UltraOptimizedCrudService, HybridCrudService, CrudService]:
        """
        Create a CRUD service with automatic optimization detection.
        """
        if auto_optimize:
            # Check if the model has complex relationships or large datasets
            # This is a simple heuristic - you can make it more sophisticated
            relationship_count = len([attr for attr in dir(model) 
                                    if not attr.startswith('_') and 
                                    hasattr(getattr(model, attr), 'property')])
            
            if relationship_count > 5 and relationship_count < 10:  # Complex model
                if ENABLE_PERF_LOGS:
                    log.logs.info(f"Using hybrid service for complex model: {model.__name__}")
                return HybridCrudService(model, db, current_user_id, use_optimized=True, fallback_to_old=True)
            elif relationship_count > 10:
                if ENABLE_PERF_LOGS:
                    log.logs.info(f"Using ultra optimized service for complex model: {model.__name__}")
                return UltraOptimizedCrudService(model, db, current_user_id)
            else:

                if ENABLE_PERF_LOGS:
                    log.logs.info(f"Using optimized service for simple model: {model.__name__}")
                return OptimizedCrudService(model, db, current_user_id)
        else:
            return CrudService(model, db, current_user_id)


# Convenience functions for easy migration
def get_optimized_crud_service(
    model: Type[DeclarativeBase],
    db: AsyncSession,
    current_user_id: Optional[str] = None
) -> OptimizedCrudService:
    """Get an optimized CRUD service instance."""
    return CrudServiceFactory.create_optimized(model, db, current_user_id)


def get_hybrid_crud_service(
    model: Type[DeclarativeBase],
    db: AsyncSession,
    current_user_id: Optional[str] = None
) -> HybridCrudService:
    """Get a hybrid CRUD service instance."""
    return CrudServiceFactory.create_hybrid(model, db, current_user_id)


def get_ultra_optimized_crud_service(
    model: Type[DeclarativeBase],
    db: AsyncSession,
    current_user_id: Optional[str] = None
) -> UltraOptimizedCrudService:
    """Get an ultra optimized CRUD service instance."""
    return CrudServiceFactory.create_ultra_optimized(model, db, current_user_id)

def get_auto_crud_service(
    model: Type[DeclarativeBase],
    db: AsyncSession,
    current_user_id: Optional[str] = None
) -> Union[OptimizedCrudService, UltraOptimizedCrudService, HybridCrudService, CrudService]:
    """Get an auto CRUD service instance."""
    return CrudServiceFactory.create_auto(model, db, current_user_id)

def migrate_to_optimized(
    old_service: CrudService,
    db: AsyncSession
) -> OptimizedCrudService:
    """Migrate from old CRUD service to optimized one."""
    return OptimizedCrudService(
        old_service.model,
        db,
        old_service.current_user_id
    )
