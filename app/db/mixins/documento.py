
from __future__ import annotations
from sqlalchemy import String, Text, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, declared_attr
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime


class DocumentoMixin:

    @declared_attr
    def nombre_archivo(cls) -> Mapped[str | None]:
        return mapped_column(String(255), nullable=True)
    
    @declared_attr
    def tipo_mime(cls) -> Mapped[str | None]:
        return mapped_column(String(100), nullable=True)
    
    @declared_attr
    def tamano_bytes(cls) -> Mapped[int | None]:
        return mapped_column(Integer, nullable=True)
    
    @declared_attr
    def hash_sha256(cls) -> Mapped[str | None]:
        return mapped_column(String(64), nullable=True)
     
    @declared_attr
    def origen(cls) -> Mapped[str | None]:
        """Origen del documento (sistema, módulo, etc.)"""
        return mapped_column(String(50), nullable=True, index=True)
 
    @declared_attr
    def origen_metadata(cls) -> Mapped[dict | None]:
        return mapped_column(JSONB, nullable=True)
    
    @declared_attr
    def descripcion(cls) -> Mapped[str | None]:
        """Descripción específica de este uso del documento"""
        return mapped_column(Text, nullable=True)
    
    @declared_attr
    def fecha_documento(cls) -> Mapped[datetime | None]:
        """Fecha del documento (puede diferir de created_at)"""
        return mapped_column(DateTime, nullable=True)
    

    # Almacenamiento y acceso
    
    @declared_attr
    def url(cls) -> Mapped[str]:
        return mapped_column(Text)
  
    @declared_attr
    def url_valida(cls) -> Mapped[bool | None]:
        return mapped_column(Boolean, nullable=True, default=None)
    
    @declared_attr
    def url_ultimo_check(cls) -> Mapped[DateTime | None]:
        return mapped_column(DateTime, nullable=True)
    
    @declared_attr
    def storage_type(cls) -> Mapped[str | None]:
        return mapped_column(String(50), nullable=True)
    