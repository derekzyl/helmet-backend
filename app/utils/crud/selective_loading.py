"""
Selective field loading system to reduce data transfer and improve performance.
This module provides intelligent field selection based on query patterns and usage.
"""

import time
from typing import Any, Dict, List, Optional, Set, Type

from sqlalchemy.orm import DeclarativeBase

from app.utils.logger import log


class SelectiveFieldLoader:
    """Intelligent field selection for database queries"""
    
    def __init__(self, model_class: Type[DeclarativeBase]):
        self.model_class = model_class
        self.field_usage_stats = {}
        self.relationship_cache = {}
        self.essential_fields = self._get_essential_fields()
        self.heavy_fields = self._get_heavy_fields()
    
    def _get_essential_fields(self) -> Set[str]:
        """Get essential fields that should always be loaded"""
        essential = {"id", "created_at", "updated_at"}
        
        # Add model-specific essential fields
        if hasattr(self.model_class, '__table__'):
            for column in self.model_class.__table__.columns:
                if column.primary_key or column.foreign_keys:
                    essential.add(column.name)
        
        return essential
    
    def _get_heavy_fields(self) -> Set[str]:
        """Get fields that are expensive to load (large text, JSON, etc.)"""
        heavy = set()
        
        if hasattr(self.model_class, '__table__'):
            for column in self.model_class.__table__.columns:
                # Mark large text fields as heavy
                length = getattr(column.type, 'length', None)
                if length and length > 1000:
                    heavy.add(column.name)
                # Mark JSON fields as heavy
                elif 'json' in str(column.type).lower():
                    heavy.add(column.name)
                # Mark text fields as heavy
                elif 'text' in str(column.type).lower():
                    heavy.add(column.name)
        
        return heavy
    
    def get_optimized_fields(self, requested_fields: Optional[List[str]] = None, context: str = "default") -> List[str]:
        """
        Get optimized field list based on context and usage patterns.
        
        Args:
            requested_fields: Fields explicitly requested
            context: Context of the query (list, detail, search, etc.)
        """
        start_time = time.time()
        
        if requested_fields:
            # If specific fields requested, use them but ensure essential fields are included
            optimized = set(requested_fields) | self.essential_fields
        else:
            # Use context-based field selection
            optimized = self._get_context_fields(context)
        
        # Remove heavy fields for list contexts unless explicitly requested
        if context in ["list", "search", "dropdown"] and not requested_fields:
            optimized -= self.heavy_fields
        
        # Convert to sorted list for consistency
        result = sorted(list(optimized))
        
        selection_time = (time.time() - start_time) * 1000
        log.logs.debug(f"🔍 [SELECTIVE_LOADING] Field selection for {self.model_class.__name__} ({context}): {selection_time:.2f}ms")
        log.logs.debug(f"   📊 Selected {len(result)} fields: {result[:5]}{'...' if len(result) > 5 else ''}")
        
        return result
    
    def _get_context_fields(self, context: str) -> Set[str]:
        """Get fields based on query context"""
        base_fields = self.essential_fields.copy()
        
        if context == "list":
            # For list views, load only essential and commonly displayed fields
            base_fields.update(self._get_common_display_fields())
        elif context == "detail":
            # For detail views, load most fields but exclude very heavy ones
            base_fields.update(self._get_all_light_fields())
        elif context == "search":
            # For search, load fields needed for search and display
            base_fields.update(self._get_search_fields())
        elif context == "dropdown":
            # For dropdowns, load only id and name/display fields
            base_fields.update(self._get_dropdown_fields())
        else:
            # Default: load all light fields
            base_fields.update(self._get_all_light_fields())
        
        return base_fields
    
    def _get_common_display_fields(self) -> Set[str]:
        """Get fields commonly used in list displays"""
        common = set()
        
        # Look for common display field patterns
        field_patterns = ["name", "title", "code", "status", "type", "category", "description"]
        
        if hasattr(self.model_class, '__table__'):
            for column in self.model_class.__table__.columns:
                if any(pattern in column.name.lower() for pattern in field_patterns):
                    common.add(column.name)
        
        return common
    
    def _get_all_light_fields(self) -> Set[str]:
        """Get all fields except heavy ones"""
        all_fields = set()
        
        if hasattr(self.model_class, '__table__'):
            for column in self.model_class.__table__.columns:
                all_fields.add(column.name)
        
        return all_fields - self.heavy_fields
    
    def _get_search_fields(self) -> Set[str]:
        """Get fields commonly used in search"""
        search_fields = set()
        
        # Look for searchable field patterns
        search_patterns = ["name", "title", "code", "description", "email", "phone"]
        
        if hasattr(self.model_class, '__table__'):
            for column in self.model_class.__table__.columns:
                if any(pattern in column.name.lower() for pattern in search_patterns):
                    search_fields.add(column.name)
        
        return search_fields
    
    def _get_dropdown_fields(self) -> Set[str]:
        """Get fields needed for dropdown displays"""
        dropdown_fields = set()
        
        # Look for dropdown display patterns
        dropdown_patterns = ["name", "title", "code", "label"]
        
        if hasattr(self.model_class, '__table__'):
            for column in self.model_class.__table__.columns:
                if any(pattern in column.name.lower() for pattern in dropdown_patterns):
                    dropdown_fields.add(column.name)
        
        return dropdown_fields
    
    def record_field_usage(self, fields: List[str], context: str):
        """Record field usage for future optimization"""
        for field in fields:
            if field not in self.field_usage_stats:
                self.field_usage_stats[field] = {"count": 0, "contexts": set()}
            
            self.field_usage_stats[field]["count"] += 1
            self.field_usage_stats[field]["contexts"].add(context)
    
    def get_field_usage_report(self) -> Dict[str, Any]:
        """Get field usage statistics"""
        return {
            "model": self.model_class.__name__,
            "total_fields": len(self.field_usage_stats),
            "essential_fields": list(self.essential_fields),
            "heavy_fields": list(self.heavy_fields),
            "field_usage": self.field_usage_stats
        }


class SelectiveLoadingManager:
    """Manager for selective field loading across models"""
    
    def __init__(self):
        self.loaders = {}
    
    def get_loader(self, model_class: Type[DeclarativeBase]) -> SelectiveFieldLoader:
        """Get or create a field loader for a model"""
        model_name = model_class.__name__
        
        if model_name not in self.loaders:
            self.loaders[model_name] = SelectiveFieldLoader(model_class)
            log.logs.debug(f"🆕 [SELECTIVE_LOADING] Created loader for {model_name}")
        
        return self.loaders[model_name]
    
    def get_optimized_fields(self, model_class: Type[DeclarativeBase], requested_fields: Optional[List[str]] = None, context: str = "default") -> List[str]:
        """Get optimized fields for a model"""
        loader = self.get_loader(model_class)
        return loader.get_optimized_fields(requested_fields, context)
    
    def record_usage(self, model_class: Type[DeclarativeBase], fields: List[str], context: str):
        """Record field usage for a model"""
        loader = self.get_loader(model_class)
        loader.record_field_usage(fields, context)
    
    def get_usage_report(self) -> Dict[str, Any]:
        """Get usage report for all models"""
        return {
            model_name: loader.get_field_usage_report()
            for model_name, loader in self.loaders.items()
        }


# Global selective loading manager
selective_loading_manager = SelectiveLoadingManager()


def get_optimized_fields(model_class: Type[DeclarativeBase], requested_fields: Optional[List[str]] = None, context: str = "default") -> List[str]:
    """Get optimized field list for a model"""
    return selective_loading_manager.get_optimized_fields(model_class, requested_fields, context)


def record_field_usage(model_class: Type[DeclarativeBase], fields: List[str], context: str):
    """Record field usage for optimization"""
    selective_loading_manager.record_usage(model_class, fields, context)


def get_loading_report() -> Dict[str, Any]:
    """Get selective loading usage report"""
    return selective_loading_manager.get_usage_report()
