# models/subvenciones.py
from __future__ import annotations
from typing import TYPE_CHECKING
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Numeric, ForeignKey


if TYPE_CHECKING:
    from app.db.base import Base
    from app.db.mixins import UUIDPKMixin, AuditMixin
    from .actuaciones import Actuacion
    from .agentes import Administracion

class ActuacionSubvencion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "actuaciones_subvenciones"
    
    actuacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones.id"), index=True)
    codigo_concesion: Mapped[str] = mapped_column(String(100), index=True)
    importe_aplicado: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    porcentaje_financiacion: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    justificacion_gasto: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    actuacion: Mapped["Actuacion"] = relationship("Actuacion", back_populates="subvenciones")
    administraciones: Mapped[list["SubvencionAdministracion"]] = relationship("SubvencionAdministracion", back_populates="subvencion", cascade="all, delete-orphan")

class SubvencionAdministracion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "subvenciones_administraciones"
    
    subvencion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones_subvenciones.id"), index=True)
    administracion_id: Mapped[str] = mapped_column(String(36), ForeignKey("administraciones.id"), index=True)
    importe_aportado: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    porcentaje_participacion: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Relaciones
    subvencion: Mapped["ActuacionSubvencion"] = relationship("ActuacionSubvencion", back_populates="administraciones")
    administracion: Mapped["Administracion"] = relationship("Administracion")
