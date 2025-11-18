# models/actuaciones.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, Numeric
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .agentes import Tecnico
    from .catalogos import RolTecnico
    from .documentos import ActuacionDocumento
    from .subvenciones import ActuacionSubvencion

class Actuacion(UUIDPKMixin, AuditMixin, Base):
    """Intervenciones/actuaciones realizadas sobre un inmueble"""
    __tablename__ = "actuaciones"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    
    # Fechas
    fecha_inicio: Mapped[Optional[datetime]] = mapped_column(index=True)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(index=True)
    
    # Presupuesto
    presupuesto: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="actuaciones")
    tecnicos: Mapped[list["ActuacionTecnico"]] = relationship("ActuacionTecnico", back_populates="actuacion", cascade="all, delete-orphan")
    documentos: Mapped[list["ActuacionDocumento"]] = relationship("ActuacionDocumento", back_populates="actuacion", cascade="all, delete-orphan")
    subvenciones: Mapped[list["ActuacionSubvencion"]] = relationship("ActuacionSubvencion", back_populates="actuacion", cascade="all, delete-orphan")

class ActuacionTecnico(UUIDPKMixin, AuditMixin, Base):
    """Técnicos asignados a una actuación con roles específicos"""
    __tablename__ = "actuaciones_tecnicos"
    
    actuacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones.id"), index=True)
    tecnico_id: Mapped[str] = mapped_column(String(36), ForeignKey("tecnicos.id"), index=True)
    rol_tecnico_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles_tecnico.id"), index=True)
    
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    fecha_inicio: Mapped[Optional[datetime]] = mapped_column(index=True)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(index=True)
    
    # Relaciones
    actuacion: Mapped["Actuacion"] = relationship("Actuacion", back_populates="tecnicos")
    tecnico: Mapped["Tecnico"] = relationship("Tecnico", back_populates="actuaciones")
    rol_tecnico: Mapped["RolTecnico"] = relationship("RolTecnico", lazy="joined")
