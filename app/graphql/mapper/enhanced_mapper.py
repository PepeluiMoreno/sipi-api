# app/graphql/mapper/enhanced_mapper.py
"""Enhanced SQLAlchemy to Strawberry Mapper"""
from typing import Type, Dict, Any, Callable, List, Optional
import strawberry
from strawberry.types import Info
from sqlalchemy.inspection import inspect
from datetime import datetime, date
from decimal import Decimal
import enum
import uuid

class EnhancedSQLAlchemyMapper:
    def __init__(self):
        self._model_properties: Dict[str, Dict[str, Any]] = {}
        self._type_cache: Dict[str, Type] = {}
    
    def type(self, model: Type) -> Type:
        """Convierte un modelo SQLAlchemy a tipo Strawberry"""
        model_name = model.__name__
        
        # Usar cache si ya existe
        if model_name in self._type_cache:
            return self._type_cache[model_name]
        
        # Obtener mapper de SQLAlchemy
        mapper = inspect(model)
        fields = {}
        
        # Mapear columnas
        for attr in mapper.attrs:
            if hasattr(attr, 'columns'):
                column = attr.columns[0]
                
                try:
                    python_type = column.type.python_type
                    field_type = self._python_to_strawberry(python_type)
                except (AttributeError, NotImplementedError):
                    # Tipos PostGIS sin python_type
                    field_type = str
                
                if column.nullable:
                    field_type = Optional[field_type]
                
                fields[attr.key] = field_type
        
        # Añadir propiedades mapeables
        properties = self._extract_properties(model)
        fields.update(properties)
        
        # Crear tipo Strawberry
        strawberry_type = strawberry.type(
            type(model_name, (), {"__annotations__": fields})
        )
        
        # Cachear
        self._type_cache[model_name] = strawberry_type
        return strawberry_type
    
    def input_type(self, model: Type, prefix: str = "", optional: bool = False) -> Type:
        """Crea InputType para crear/actualizar"""
        mapper = inspect(model)
        fields = {}
        
        for attr in mapper.attrs:
            if hasattr(attr, 'columns'):
                column = attr.columns[0]
                
                # Skip primary keys en Create
                if column.primary_key and prefix.lower() == "create":
                    continue
                
                try:
                    python_type = column.type.python_type
                    field_type = self._python_to_strawberry(python_type)
                except (AttributeError, NotImplementedError):
                    field_type = str
                
                if optional or column.nullable or column.default is not None:
                    field_type = Optional[field_type]
                
                fields[attr.key] = field_type
        
        type_name = f"{model.__name__}{prefix}Input"
        return strawberry.input(type(type_name, (), {"__annotations__": fields}))
    
    def _extract_properties(self, model: Type) -> Dict[str, Type]:
        """Extrae propiedades y métodos del modelo"""
        properties = {}
        
        # ✅ SOLO ignorar metadata de SQLAlchemy
        ignored_properties = {'metadata', 'registry'}
        
        for attr_name in dir(model):
            if attr_name.startswith('_'):
                continue
            
            if attr_name in ignored_properties:
                continue
            
            try:
                attr = getattr(model, attr_name)
                
                if isinstance(attr, property):
                    ret_type = self._infer_return_type(attr)
                    properties[attr_name] = ret_type
                    
            except Exception:
                continue
        
        return properties
    
    def _infer_return_type(self, attr: Any) -> Type:
        """Infiere el tipo de retorno de una propiedad/método"""
        try:
            func = attr.fget if isinstance(attr, property) else attr
            
            # ✅ Si tiene anotación, usarla
            if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                return func.__annotations__['return']
            
            # ✅ Inferir por nombre
            name = getattr(func, '__name__', '').lower()
            
            if name.startswith(('is_', 'has_', 'tiene_', 'esta_')):
                return bool
            
            if 'count' in name or 'total' in name:
                return int
            
            # ✅ Para propiedades sin anotación que retornan listas/objetos
            if 'titulares' in name or name.endswith('_list') or name.endswith('s'):
                return str  # Representar como string en GraphQL
            
            if 'actual' in name or 'current' in name:
                return Optional[str]  # Representar como string nullable
            
            return str
        except:
            return str
    
    def _python_to_strawberry(self, py_type: Type) -> Type:
        """Convierte tipos Python a tipos Strawberry"""
        if isinstance(py_type, type) and issubclass(py_type, enum.Enum):
            return py_type
        if py_type == uuid.UUID:
            return strawberry.ID
        
        mapping = {
            int: int,
            str: str,
            float: float,
            bool: bool,
            datetime: datetime,
            date: date,
            Decimal: float,
        }
        return mapping.get(py_type, str)