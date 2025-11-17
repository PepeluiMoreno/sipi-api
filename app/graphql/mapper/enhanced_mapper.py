"""Enhanced SQLAlchemy to Strawberry Mapper"""
from typing import Type, Dict, Any, Callable, List, Optional
import strawberry
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper
from strawberry.types import Info
from sqlalchemy.inspection import inspect
from datetime import datetime, date
from decimal import Decimal
import enum
import uuid

class EnhancedSQLAlchemyMapper(StrawberrySQLAlchemyMapper):
    def __init__(self):
        super().__init__()
        self._model_properties: Dict[str, Dict[str, Any]] = {}
    
    def type(self, model: Type) -> Type:
        strawberry_type = super().type(model)
        self._add_properties(model, strawberry_type)
        return strawberry_type
    
    def input_type(self, model: Type, prefix: str = "", optional: bool = False) -> Type:
        mapper = inspect(model)
        fields = {}
        
        for attr in mapper.attrs:
            if hasattr(attr, 'columns'):
                column = attr.columns[0]
                if column.primary_key and prefix.lower() == "create":
                    continue
                
                field_type = self._python_to_strawberry(column.type.python_type)
                if optional or column.nullable or column.default:
                    field_type = Optional[field_type]
                
                fields[attr.key] = field_type
        
        type_name = f"{model.__name__}{prefix}Input"
        return strawberry.input(type(type_name, (), {"__annotations__": fields}))
    
    def _add_properties(self, model: Type, strawberry_type: Type):
        properties = {}
        
        for attr_name in dir(model):
            if attr_name.startswith('_') or attr_name in dir(strawberry_type):
                continue
            
            attr = getattr(model, attr_name)
            
            if isinstance(attr, property):
                properties[attr_name] = {
                    'type': self._infer_return_type(attr),
                    'callable': False
                }
            elif (callable(attr) and not isinstance(attr, type) and 
                  hasattr(attr, '__name__') and not attr_name.startswith('_')):
                
                if any(attr_name.startswith(p) for p in ('query', 'metadata', 'sa_', 'registry')):
                    continue
                
                properties[attr_name] = {
                    'type': self._infer_return_type(attr),
                    'callable': True,
                    'async': self._is_async(attr)
                }
        
        for name, info in properties.items():
            strawberry_type.__annotations__[name] = info['type']
            resolver = self._create_resolver(name, info)
            setattr(strawberry_type, name, strawberry.field(resolver))
        
        self._model_properties[model.__name__] = properties
    
    def _infer_return_type(self, attr: Any) -> Type:
        try:
            func = attr.fget if isinstance(attr, property) else attr
            
            if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                return func.__annotations__['return']
            
            name = getattr(func, '__name__', '').lower()
            if name.startswith(('is_', 'has_', 'tiene_')):
                return bool
            if name.startswith('get_') or name.endswith('_list'):
                return List[Any]
            if 'count' in name or 'total' in name:
                return int
            
            return str
        except:
            return str
    
    def _is_async(self, method: Callable) -> bool:
        return hasattr(method, '__code__') and method.__code__.co_flags & 0x80
    
    def _create_resolver(self, prop_name: str, prop_info: Dict) -> Callable:
        from app.graphql.decorators import async_safe_resolver
        
        @async_safe_resolver
        async def resolver(root, info: Info):
            value = getattr(root, prop_name)
            if prop_info['callable'] and callable(value):
                result = value()
                if prop_info['async']:
                    return await result
                return result
            return value
        
        return resolver
    
    def _python_to_strawberry(self, py_type: Type) -> Type:
        if isinstance(py_type, type) and issubclass(py_type, enum.Enum):
            return py_type
        if py_type == uuid.UUID:
            return strawberry.ID
        
        mapping = {
            int: int, str: str, float: float, bool: bool,
            datetime: datetime, date: date, Decimal: float,
        }
        return mapping.get(py_type, str)
