# app/graphql/mapper/enhanced_mapper.py
"""Enhanced SQLAlchemy to Strawberry Mapper"""
from typing import Type, Dict, Any, Callable, List, Optional, get_origin, get_args
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
                    # ✅ Si retorna None, ignorar esta propiedad (tipo complejo no mapeable)
                    if ret_type is not None:
                        properties[attr_name] = ret_type
                    
            except Exception:
                continue
        
        return properties
    
    def _infer_return_type(self, attr: Any) -> Optional[Type]:
        """Infiere el tipo de retorno de una propiedad/método. Retorna None si no es mapeable."""
        try:
            func = attr.fget if isinstance(attr, property) else attr
            
            # ✅ Si tiene anotación, analizarla
            if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                ann = func.__annotations__['return']
                
                # ✅ Detectar tipos complejos no mapeables
                ann_str = str(ann)
                
                # Ignorar list[Model], List[Model], etc.
                if 'list[' in ann_str.lower() or 'List[' in ann_str:
                    # Verificar si es list de tipos primitivos o de modelos
                    origin = get_origin(ann)
                    if origin is list or origin is List:
                        args = get_args(ann)
                        if args:
                            # Si el argumento no es un tipo primitivo, ignorar
                            arg_type = args[0]
                            if not self._is_primitive_type(arg_type):
                                return None  # ✅ Ignorar list[Model]
                
                # Tipos válidos
                if ann in (str, int, float, bool, datetime, date):
                    return ann
                
                # Optional[str], Optional[int], etc.
                if get_origin(ann) is type(Optional):
                    args = get_args(ann)
                    if args and self._is_primitive_type(args[0]):
                        return ann
                
                return ann  # Confiar en otros tipos anotados
            
            # ✅ Inferir por nombre (sin anotación)
            name = getattr(func, '__name__', '').lower()
            
            if name.startswith(('is_', 'has_', 'tiene_', 'esta_')):
                return bool
            
            if 'count' in name or 'total' in name:
                return int
            
            # Para propiedades complejas sin anotación
            if name.endswith(('_list', '_items', '_all')):
                return None  # Ignorar
            
            if 'actual' in name or 'current' in name or 'principal' in name:
                return Optional[str]
            
            return str
        except:
            return str
    
    def _is_primitive_type(self, t: Type) -> bool:
        """Verifica si un tipo es primitivo/básico"""
        primitives = (str, int, float, bool, datetime, date, Decimal, type(None))
        
        # Tipo directo
        if t in primitives:
            return True
        
        # Enum
        if isinstance(t, type) and issubclass(t, enum.Enum):
            return True
        
        # Tipos genéricos como Optional[str]
        origin = get_origin(t)
        if origin is type(Optional):
            args = get_args(t)
            return args and args[0] in primitives
        
        return False
    
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