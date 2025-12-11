# models/transmisiones.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Numeric, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin


class Transmision(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "transmisiones"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    transmitente_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transmitentes.id"), index=True)
    adquiriente_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("adquirientes.id"), index=True)
    notaria_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("notarias.id"), index=True)
    registro_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("registros_propiedad.id"), index=True)
    tipo_transmision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_transmision.id"), index=True)
    tipo_certificacion_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_certificacion_propiedad.id"), index=True)
    
    fecha_transmision: Mapped[Optional[datetime]] = mapped_column(index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    precio_venta: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="transmisiones", foreign_keys=[inmueble_id])
    transmitente: Mapped[Optional["Transmitente"]] = relationship("Transmitente", back_populates="transmisiones")
    adquiriente: Mapped[Optional["Adquiriente"]] = relationship("Adquiriente", back_populates="transmisiones")
    notaria: Mapped[Optional["Notaria"]] = relationship("Notaria", back_populates="transmisiones")
    registro_propiedad: Mapped[Optional["RegistroPropiedad"]] = relationship("RegistroPropiedad", back_populates="transmisiones")
    tipo_transmision: Mapped[Optional["TipoTransmision"]] = relationship("TipoTransmision", back_populates="transmisiones")
    tipo_certificacion_propiedad: Mapped[Optional["TipoCertificacionPropiedad"]] = relationship("TipoCertificacionPropiedad", back_populates="transmisiones")
    documentos: Mapped[list["TransmisionDocumento"]] = relationship("TransmisionDocumento", back_populates="transmision", cascade="all, delete-orphan")
    anunciantes: Mapped[list["TransmisionAnunciante"]] = relationship("TransmisionAnunciante", back_populates="transmision", cascade="all, delete-orphan")

class TransmisionAnunciante(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "transmision_anunciantes"
    
    transmision_id: Mapped[str] = mapped_column(String(36), ForeignKey("transmisiones.id"), index=True)
    agencia_inmobiliaria_id: Mapped[str] = mapped_column(String(36), ForeignKey("agencias_inmobiliarias.id"), index=True)
    
    # Relaciones
    transmision: Mapped["Transmision"] = relationship("Transmision", back_populates="anunciantes")
    agencia_inmobiliaria: Mapped["AgenciaInmobiliaria"] = relationship("AgenciaInmobiliaria", back_populates="transmisiones_anunciadas")
