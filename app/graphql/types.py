import strawberry
from typing import List, Optional, Generic, TypeVar
from enum import Enum

# PageInfo SIN decorador (se registra en schema.py)
class PageInfo:
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_previous: bool

# PaginatedResult genérico para uso interno
T = TypeVar('T')

class PaginatedResult(Generic[T]):
    def __init__(self, items: List[T], page_info: PageInfo):
        self.items = items
        self.page_info = page_info

@strawberry.enum
class FilterOperator(Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    LIKE = "like"
    ILIKE = "ilike"
    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    BETWEEN = "between"

@strawberry.input
class FilterInput:
    field: str
    operator: FilterOperator = FilterOperator.EQ
    value: Optional[str] = None
    values: Optional[List[str]] = None

@strawberry.input
class SortInput:
    field: str
    direction: str = "asc"

@strawberry.input
class PaginationInput:
    page: int = 1
    page_size: int = 20