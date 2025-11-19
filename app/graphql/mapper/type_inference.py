# app/graphql/mapper/type_inference.py
"""Type inference from Python to Strawberry"""
from typing import Type, Optional, List, get_args, Any
from datetime import datetime, date
from decimal import Decimal
import enum

from .utils import is_list_of_primitives

class TypeInferencer:
    """Infiere tipos Strawberry desde propiedades Python"""
    
    @staticmethod
    def infer_from_property(attr: Any) -> Optional[Type]:
        """
        Infiere tipo de retorno de una propiedad.
        Retorna None si no es mapeable.
        """
        try:
            func = attr.fget if isinstance(attr, property) else attr
            name = getattr(func, '__name__', '').lower()
            
            # Inferir por nombre
            if name.startswith(('is_', 'has_', 'tiene_', 'esta_')):
                return bool
            
            if 'count' in name or 'total' in name or name.endswith('_count'):
                return int
            
            # Analizar anotación
            if hasattr(func, '__annotations__') and 'return' in func.__annotations__:
                ann = func.__annotations__['return']
                ann_str = str(ann)
                
                # List[str], List[int] → Permitir
                if is_list_of_primitives(ann_str):
                    if 'List[str]' in ann_str or 'list[str]' in ann_str:
                        return List[str]
                    if 'List[int]' in ann_str or 'list[int]' in ann_str:
                        return List[int]
                
                # List[Model] → Ignorar
                if '[' in ann_str and not is_list_of_primitives(ann_str):
                    return None
                
                # Tipos básicos
                if ann in (str, int, float, bool, datetime, date):
                    return ann
                
                # Optional[tipo_basico]
                if 'Optional[' in ann_str:
                    try:
                        args = get_args(ann)
                        if args and args[0] in (str, int, float, bool, datetime, date):
                            return ann
                    except:
                        pass
                
                # Enum
                try:
                    if isinstance(ann, type) and issubclass(ann, enum.Enum):
                        return ann
                except:
                    pass
            
            # Propiedades _lista, _list → List[str]
            if name.endswith(('_lista', '_list', '_nombres', '_ids')):
                return List[str]
            
            return Optional[str]
            
        except Exception:
            return None