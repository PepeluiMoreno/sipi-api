# app/graphql/mapper/utils.py
"""Utility functions for type mapping"""
from typing import Type, get_origin, get_args, Optional
import enum
from datetime import datetime, date
from decimal import Decimal

def is_primitive_type(t: Type) -> bool:
    """Verifica si un tipo es primitivo/básico"""
    primitives = (str, int, float, bool, datetime, date, Decimal, type(None))
    
    if t in primitives:
        return True
    
    if isinstance(t, type) and issubclass(t, enum.Enum):
        return True
    
    origin = get_origin(t)
    if origin is type(Optional):
        args = get_args(t)
        return args and args[0] in primitives
    
    return False

def is_list_of_primitives(ann_str: str) -> bool:
    """¿Es List[str], List[int], etc?"""
    if 'List[str]' in ann_str or 'list[str]' in ann_str:
        return True
    if 'List[int]' in ann_str or 'list[int]' in ann_str:
        return True
    if 'List[float]' in ann_str or 'list[float]' in ann_str:
        return True
    if 'List[bool]' in ann_str or 'list[bool]' in ann_str:
        return True
    return False