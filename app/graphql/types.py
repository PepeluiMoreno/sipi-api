"""Core GraphQL Types"""
import strawberry
from typing import Generic, TypeVar, List, Optional, Any
from enum import Enum

T = TypeVar("T")

@strawberry.type
class PageInfo:
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

@strawberry.type
class PaginatedResult(Generic[T]):
    items: List[T]
    page_info: PageInfo

# ✅ Usar @strawberry.enum para GraphQL
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
    value: Optional[Any] = None
    values: Optional[List[Any]] = None

@strawberry.input
class SortInput:
    field: str
    direction: str = "asc"

@strawberry.input
class PaginationInput:
    page: int = 1
    page_size: int = 20
    
    def __post_init__(self):
        self.page = max(1, self.page)
        self.page_size = min(max(1, self.page_size), 100)
