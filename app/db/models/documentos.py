# models/documentos.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .actuaciones import Actuacion
    from .transmisiones import Transmision
    from .catalogos import TipoDocumento

class Documento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "documentos"
    
    url: Mapped[str] = mapped_column(Text)
    nombre_archivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamano_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

class InmuebleDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_documentos"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id"), index=True)
    tipo_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("tipos_documento.id"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_documento: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="documentos")
    tipo_documento: Mapped["TipoDocumento"] = relationship("TipoDocumento", back_populates="inmuebles_documentos")

class ActuacionDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "actuaciones_documentos"
    
    actuacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones.id"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id"), index=True)
    tipo_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("tipos_documento.id"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    actuacion: Mapped["Actuacion"] = relationship("Actuacion", back_populates="documentos")
    tipo_documento: Mapped["TipoDocumento"] = relationship("TipoDocumento", back_populates="actuaciones_documentos")

class TransmisionDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "transmisiones_documentos"
    
    transmision_id: Mapped[str] = mapped_column(String(36), ForeignKey("transmisiones.id"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id"), index=True)
    tipo_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("tipos_documento.id"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    transmision: Mapped["Transmision"] = relationship("Transmision", back_populates="documentos")
    tipo_documento: Mapped["TipoDocumento"] = relationship("TipoDocumento", back_populates="transmisiones_documentos")
