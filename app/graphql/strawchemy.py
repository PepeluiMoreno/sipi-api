# app/graphql/strawchemy.py
import strawberry
from typing import List, Optional, TypeVar, Generic, Any, Type, Dict
from enum import Enum
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import or_, and_, not_
from sqlalchemy.orm import InstrumentedAttribute
import inspect

# -----------------------------------------------------------------------------
# 1. Tipos de Filtro Genéricos
# -----------------------------------------------------------------------------

T = TypeVar("T")

@strawberry.input
class FilterOperations(Generic[T]):
    eq: Optional[T] = None
    ne: Optional[T] = None
    gt: Optional[T] = None
    gte: Optional[T] = None
    lt: Optional[T] = None
    lte: Optional[T] = None
    in_: Optional[List[T]] = strawberry.field(default=None, name="in")
    not_in: Optional[List[T]] = None
    is_null: Optional[bool] = None

@strawberry.input
class StringFilterOperations(FilterOperations[str]):
    like: Optional[str] = None
    ilike: Optional[str] = None
    contains: Optional[str] = None
    startswith: Optional[str] = None
    endswith: Optional[str] = None

# Definimos tipos concretos para usar en los inputs
@strawberry.input
class IntFilter(FilterOperations[int]):
    pass

@strawberry.input
class FloatFilter(FilterOperations[float]):
    pass

@strawberry.input
class BooleanFilter(FilterOperations[bool]):
    pass

@strawberry.input
class IDFilter(FilterOperations[strawberry.ID]):
    pass

@strawberry.input
class DateFilter(FilterOperations[str]): 
    # Usamos string para fechas en input GraphQL por simplicidad
    pass

# -----------------------------------------------------------------------------
# 2. Factory de Inputs Dinámicos
# -----------------------------------------------------------------------------

_filter_input_cache: Dict[str, Type] = {}

def get_filter_type_for_python_type(py_type: Type) -> Type:
    """Mapea tipos Python a tipos de Filtro Strawberry"""
    if py_type == int:
        return Optional[IntFilter]
    elif py_type == float or py_type == Decimal:
        return Optional[FloatFilter]
    elif py_type == bool:
        return Optional[BooleanFilter]
    elif py_type == datetime or py_type == date:
        return Optional[DateFilter]
    elif py_type == str:
        return Optional[StringFilterOperations]
    # Default a String para casos complejos
    return Optional[StringFilterOperations]

def create_filter_input_type(model: Type, type_name_prefix: str = "") -> Type:
    """
    Crea dinámicamente un Input Type de Strawberry con campos de filtro 
    para cada columna del modelo SQLAlchemy.
    """
    model_name = model.__name__
    input_name = f"{type_name_prefix}{model_name}FilterInput"

    if input_name in _filter_input_cache:
        return _filter_input_cache[input_name]

    # Campos base
    annotations: Dict[str, Any] = {}
    
    # 1. Campos de columnas
    if hasattr(model, '__table__'):
        for column in model.__table__.columns:
            # Detectar tipo
            try:
                python_type = column.type.python_type
                if column.name == 'id':
                     annotations[column.name] = Optional[IDFilter]
                else:
                    annotations[column.name] = get_filter_type_for_python_type(python_type)
            except NotImplementedError:
                # Tipos geoespaciales u otros complejos
                continue

    # 2. Construir la clase
    # Necesitamos definir la clase primero para poder referenciarla en _and / _or (Self reference)
    
    # Usamos un hack para tipos recursivos en runtime construct: 
    # Strawberry no soporta fácil tipos recursivos autogenerados sin definir la clase explicitamente.
    # Pero podemos usar Lazy Types o simplemente definir _and/_or como List['InputName'] si fuera static.
    # Para dynamic, lo haremos en dos pasos.

    # Paso A: Crear la clase sin _and/_or
    cls = type(input_name, (), {"__annotations__": annotations})
    
    # Paso B: Decorar con strawberry.input
    input_type = strawberry.input(cls)
    
    # Paso C: Añadir _and y _or dinámicamente? 
    # Strawberry valida las anotaciones al decorar. 
    # Una opción robusta es permitir _and / _or como JSON genérico o simplificar 
    # y no soportar anidamiento infinito recursivo en la definición del tipo, 
    # sino solo 1 nivel si fuera necesario, pero Strawchemy frontend pide recursivo.
    
    # Solución: Usar List[Any] para _and/_or temporalmente o definir fields opcionales manualmente
    # Nota: Strawberry permite `List["TypeName"]` lazy.
    
    # Re-intentamos definiendo la clase de forma completa con anotaciones lazy
    annotations["_and"] = Optional[List[input_type]]
    annotations["_or"] = Optional[List[input_type]]
    
    # Recargamos la clase con las nuevas anotaciones
    cls = type(input_name, (), {"__annotations__": annotations})
    input_type = strawberry.input(cls)

    _filter_input_cache[input_name] = input_type
    return input_type

# -----------------------------------------------------------------------------
# 3. Query Builder (SQLAlchemy)
# -----------------------------------------------------------------------------

def apply_strawchemy_filters(query, filter_input: Any, model: Type):
    """
    Aplica los filtros del input Strawberry a la query SQLAlchemy.
    Recursivo para _and / _or.
    """
    if not filter_input:
        return query

    conditions = _build_conditions(filter_input, model)
    if conditions:
        query = query.where(and_(*conditions))
    
    return query

def _build_conditions(filter_input: Any, model: Type) -> List[Any]:
    conditions = []
    
    # Iterar sobre los campos del input
    # filter_input es una instancia de la clase generada por strawberry
    
    # Convertir a dict para iterar fácil, saltando nulos
    data = vars(filter_input) if hasattr(filter_input, "__dict__") else {}
    
    for field, value in data.items():
        if value is None:
            continue
            
        if field == "_and":
            # value es List[FilterInput]
            and_conditions = []
            for sub_filter in value:
                subs = _build_conditions(sub_filter, model)
                if subs:
                    and_conditions.append(and_(*subs))
            if and_conditions:
                conditions.append(and_(*and_conditions))
                
        elif field == "_or":
            # value es List[FilterInput]
            or_conditions = []
            for sub_filter in value:
                subs = _build_conditions(sub_filter, model)
                if subs:
                    # Dentro de un OR, cada elemento de la lista es una condición
                    # Si subs devuelve varias (implícito AND), las juntamos
                    or_conditions.append(and_(*subs))
            if or_conditions:
                conditions.append(or_(*or_conditions))
                
        else:
            # Es un campo del modelo (ej: 'nombre', 'edad')
            if hasattr(model, field):
                column = getattr(model, field)
                field_conditions = _build_field_conditions(column, value)
                if field_conditions:
                    conditions.append(field_conditions)
    
    return conditions

def _build_field_conditions(column: InstrumentedAttribute, operation_input: Any):
    # operation_input es ej: StringFilterOperations(ilike="%abc%", eq=None)
    ops = vars(operation_input) if hasattr(operation_input, "__dict__") else {}
    
    res_conditions = []
    
    for op, val in ops.items():
        if val is None:
            continue
            
        if op == "eq":
            res_conditions.append(column == val)
        elif op == "ne":
            res_conditions.append(column != val)
        elif op == "gt":
            res_conditions.append(column > val)
        elif op == "gte":
            res_conditions.append(column >= val)
        elif op == "lt":
            res_conditions.append(column < val)
        elif op == "lte":
            res_conditions.append(column <= val)
        elif op == "in_": # Strawberry mapea 'in' a 'in_' campo python
             res_conditions.append(column.in_(val))
        elif op == "not_in":
            res_conditions.append(column.not_in(val))
        elif op == "is_null":
            if val is True:
                res_conditions.append(column.is_(None))
            else:
                res_conditions.append(column.is_not(None))
        elif op == "like":
            res_conditions.append(column.like(val))
        elif op == "ilike":
            res_conditions.append(column.ilike(val))
        elif op == "contains":
            res_conditions.append(column.contains(val))
        elif op == "startswith":
            res_conditions.append(column.startswith(val))
        elif op == "endswith":
            res_conditions.append(column.endswith(val))
            
    if len(res_conditions) == 1:
        return res_conditions[0]
    elif len(res_conditions) > 1:
        return and_(*res_conditions)
    
    return None
