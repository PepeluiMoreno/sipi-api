# Package
# app/graphql/mapper/__init__.py
"""SQLAlchemy to Strawberry GraphQL Mapper"""

# ✅ Nuevo mapper (con librería)
from .base import SQLAlchemyMapper

# ✅ Viejo mapper (respaldo)
from .enhanced_mapper import EnhancedSQLAlchemyMapper

# Exportar ambos
__all__ = [
    'SQLAlchemyMapper',           # Nuevo (por defecto)
    'EnhancedSQLAlchemyMapper',   # Viejo (respaldo)
]