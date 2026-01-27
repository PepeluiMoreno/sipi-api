# ETL/common/__init__.py
"""
Módulo compartido para procesos ETL.
Contiene utilidades comunes para resolución geográfica usando códigos INE.
"""

from .ine_constants import (
    CCAA_OFICIAL,
    PROVINCIA_A_CCAA,
    NOMBRES_PROVINCIAS,
    ALIAS_PROVINCIAS,
    ALIAS_MUNICIPIOS,
)
from .ine_resolver import INEResolver

__all__ = [
    'CCAA_OFICIAL',
    'PROVINCIA_A_CCAA',
    'NOMBRES_PROVINCIAS',
    'ALIAS_PROVINCIAS',
    'ALIAS_MUNICIPIOS',
    'INEResolver',
]
