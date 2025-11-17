# models/proteccion.py
from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey

if TYPE_CHECKING:
    from app.db.base import Base
    from app.db.mixins import UUIDPKMixin, AuditMixin
    from .inmuebles import Inmueble
    from .catalogos import FiguraProteccion
    from .agentes import Administracion

class InmuebleFiguraProteccion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_figuras_proteccion"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    figura_proteccion_id: Mapped[str] = mapped_column(String(36), ForeignKey("figuras_proteccion.id"), index=True)
    administracion_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("administraciones.id"), index=True, nullable=True)
    bic_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    norma: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_declaracion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="figuras_proteccion")
    figura_proteccion: Mapped["FiguraProteccion"] = relationship("FiguraProteccion")
    administracion: Mapped["Administracion"] = relationship("Administracion")
