# models/historiografia.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, ForeignKey

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
   from .inmuebles import Inmueble

class FuenteHistoriografica(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "fuentes_historiograficas"
    
    titulo: Mapped[str] = mapped_column(String(500), index=True)
    autor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    editorial: Mapped[str | None] = mapped_column(String(255), nullable=True)
    anno_publicacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    citas: Mapped[list["CitaHistoriografica"]] = relationship("CitaHistoriografica", back_populates="fuente", cascade="all, delete-orphan")

class CitaHistoriografica(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "citas_historiograficas"
    
    fuente_id: Mapped[str] = mapped_column(String(36), ForeignKey("fuentes_historiograficas.id"), index=True)
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    paginas: Mapped[str | None] = mapped_column(String(100), nullable=True)
    texto_cita: Mapped[str] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    fuente: Mapped["FuenteHistoriografica"] = relationship("FuenteHistoriografica", back_populates="citas")
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="citas_historiograficas")
