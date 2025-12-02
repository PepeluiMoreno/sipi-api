# models/documentos.py
from __future__ import annotations
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin, DocumentoMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .actuaciones import Actuacion
    from .transmisiones import Transmision
    from .tipologias import TipoDocumento, TipoLicencia, FuenteDocumental

class Documento(UUIDPKMixin, AuditMixin, DocumentoMixin, Base):
    __tablename__ = "documentos"
    tipo_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("tipos_documento.id", ondelete="RESTRICT"), index=True)
    tipo_licencia_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_licencia.id", ondelete="RESTRICT"), index=True)
    fuente_documental_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("fuentes_documentales.id", ondelete="RESTRICT"), index=True)
    inmuebles: Mapped[list["InmuebleDocumento"]] = relationship("InmuebleDocumento", back_populates="documento", cascade="all, delete-orphan")
    actuaciones: Mapped[list["ActuacionDocumento"]] = relationship("ActuacionDocumento", back_populates="documento", cascade="all, delete-orphan")
    transmisiones: Mapped[list["TransmisionDocumento"]] = relationship("TransmisionDocumento", back_populates="documento", cascade="all, delete-orphan")
    tipo_documento: Mapped["TipoDocumento"] = relationship("TipoDocumento", back_populates="documentos")
    tipo_licencia: Mapped[Optional["TipoLicencia"]] = relationship("TipoLicencia", back_populates="documentos")
    fuente_documental: Mapped[Optional["FuenteDocumental"]] = relationship("FuenteDocumental", back_populates="documentos")

class InmuebleDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_documentos"
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id", ondelete="CASCADE"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="documentos")
    documento: Mapped["Documento"] = relationship("Documento", back_populates="inmuebles")

class ActuacionDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "actuaciones_documentos"
    actuacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones.id", ondelete="CASCADE"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    actuacion: Mapped["Actuacion"] = relationship("Actuacion", back_populates="documentos")
    documento: Mapped["Documento"] = relationship("Documento", back_populates="actuaciones")

class TransmisionDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "transmisiones_documentos"
    transmision_id: Mapped[str] = mapped_column(String(36), ForeignKey("transmisiones.id", ondelete="CASCADE"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id", ondelete="CASCADE"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    transmision: Mapped["Transmision"] = relationship("Transmision", back_populates="documentos")
    documento: Mapped["Documento"] = relationship("Documento", back_populates="transmisiones")

