# app/graphql/mapper/cache.py
"""Cache management for type conversions"""
from typing import Dict, Type

class TypeCache:
    """Caché para tipos convertidos"""
    
    def __init__(self):
        self._type_cache: Dict[str, Type] = {}
    
    def get_type(self, model_name: str) -> Type | None:
        return self._type_cache.get(model_name)
    
    def set_type(self, model_name: str, strawberry_type: Type):
        self._type_cache[model_name] = strawberry_type
    
    def has_type(self, model_name: str) -> bool:
        return model_name in self._type_cache
    
    def get_all_types(self) -> Dict[str, Type]:
        return self._type_cache.copy()
    
    def clear(self):
        self._type_cache.clear()