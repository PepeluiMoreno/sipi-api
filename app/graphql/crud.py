# crud.py
"""CRUD Resolver with Advanced Filters"""
from typing import Type, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, asc, desc
from sqlalchemy.exc import NoResultFound
from datetime import datetime, timezone  # ✅ IMPORT CORREGIDO
from app.graphql.types import FilterInput, SortInput, PaginationInput, PaginatedResult, PageInfo

class CRUDResolver:
    def __init__(self, model: Type, mapper):
        self.model = model
        self.mapper = mapper
    
    async def get(self, session: AsyncSession, id: Any) -> Any:
        stmt = select(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if not instance:
            raise NoResultFound(f"{self.model.__name__} con id {id} no encontrado")
        return instance
    
    async def list(self, session: AsyncSession,
                   filters: Optional[List[FilterInput]] = None,
                   sort: Optional[List[SortInput]] = None,
                   pagination: Optional[PaginationInput] = None) -> PaginatedResult:
        stmt = select(self.model)
        
        if filters:
            stmt = self._apply_filters(stmt, filters)
        
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = await session.scalar(count_stmt) or 0
        
        if sort:
            stmt = self._apply_sort(stmt, sort)
        
        page = pagination.page if pagination else 1
        page_size = pagination.page_size if pagination else 20
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        
        result = await session.execute(stmt)
        items = list(result.scalars().all())
        
        total_pages = (total + page_size - 1) // page_size
        
        return PaginatedResult(
            items=items,
            page_info=PageInfo(
                page=page, page_size=page_size, total=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1
            )
        )
    
    def _apply_filters(self, stmt, filters: List[FilterInput]):
        for f in filters:
            column = getattr(self.model, f.field, None)
            if not column:
                continue
            
            op = f.operator.value if hasattr(f.operator, 'value') else f.operator
            value = f.value
            values = f.values or []
            
            if op == "eq":
                stmt = stmt.where(column == value)
            elif op == "ne":
                stmt = stmt.where(column != value)
            elif op == "gt":
                stmt = stmt.where(column > value)
            elif op == "gte":
                stmt = stmt.where(column >= value)
            elif op == "lt":
                stmt = stmt.where(column < value)
            elif op == "lte":
                stmt = stmt.where(column <= value)
            elif op == "like":
                stmt = stmt.where(column.like(f"%{value}%"))
            elif op == "ilike":
                stmt = stmt.where(column.ilike(f"%{value}%"))
            elif op == "in":
                stmt = stmt.where(column.in_(values))
            elif op == "not_in":
                stmt = stmt.where(column.not_in(values))
            elif op == "is_null":
                stmt = stmt.where(column.is_(None) if value else column.is_not(None))
            elif op == "between" and len(values) == 2:
                stmt = stmt.where(column.between(values[0], values[1]))
        
        return stmt
    
    def _apply_sort(self, stmt, sort: List[SortInput]):
        for s in sort:
            column = getattr(self.model, s.field, None)
            if not column:
                continue
            
            if s.direction.lower() == "desc":
                stmt = stmt.order_by(desc(column))
            else:
                stmt = stmt.order_by(asc(column))
        
        return stmt
    
    async def create(self, session: AsyncSession, data: dict) -> Any:
        instance = self.model(**data)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance
    
    async def update(self, session: AsyncSession, id: Any, data: dict) -> Any:
        stmt = select(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if not instance:
            raise NoResultFound(f"{self.model.__name__} con id {id} no encontrado")
        
        for key, value in data.items():
            if hasattr(instance, key) and value is not None:
                setattr(instance, key, value)
        
        await session.commit()
        await session.refresh(instance)
        return instance
    
    async def delete(self, session: AsyncSession, id: Any) -> bool:
        stmt = select(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if not instance:
            return False
        
        if hasattr(instance, 'deleted_at'):
            instance.deleted_at = datetime.now(timezone.utc)  # ✅ CORREGIDO
        else:
            # ✅ CORREGIDO: await necesario en SQLAlchemy 2.0+
            await session.delete(instance)
        
        await session.commit()
        return True
    
    async def restore(self, session: AsyncSession, id: Any) -> Optional[Any]:
        if not hasattr(self.model, 'deleted_at'):
            return None
        
        stmt = select(self.model).where(self.model.id == id)
        result = await session.execute(stmt)
        instance = result.scalar_one_or_none()
        if not instance or not instance.deleted_at:
            return None
        
        instance.deleted_at = None
        await session.commit()
        await session.refresh(instance)
        return instance