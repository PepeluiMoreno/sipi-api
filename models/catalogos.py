# models/catalogos.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .agentes import Tecnico
    from .transmisiones import Transmision, Inmatriculacion
    from .inmuebles import Inmueble

class CatalogoBase(UUIDPKMixin, AuditMixin, Base):
    """Base para catálogos simples (nombre + descripción)"""
    __abstract__ = True
    
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

class EstadoConservacion(CatalogoBase):
    __tablename__ = "estados_conservacion"
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="estado_conservacion")

class EstadoTratamiento(CatalogoBase):
    __tablename__ = "estados_tratamiento"
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="estado_tratamiento")

class FiguraProteccion(CatalogoBase):
    __tablename__ = "figuras_proteccion"

class RolTecnico(CatalogoBase):
    __tablename__ = "roles_tecnico"
    tecnicos: Mapped[list["Tecnico"]] = relationship("Tecnico", back_populates="rol_tecnico")

class TipoCertificacionPropiedad(CatalogoBase):
    __tablename__ = "tipos_certificacion_propiedad"
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="tipo_certificacion_propiedad")
    inmatriculaciones: Mapped[list["Inmatriculacion"]] = relationship("Inmatriculacion", back_populates="tipo_certificacion_propiedad")

class TipoDocumento(CatalogoBase):
    __tablename__ = "tipos_documento"

class TipoInmueble(CatalogoBase):
    __tablename__ = "tipos_inmueble"
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="tipo_inmueble")

class TipoMimeDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "tipos_mime_documento"
    tipo_mime: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    extension: Mapped[str] = mapped_column(String(10))
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)

class TipoPersona(CatalogoBase):
    __tablename__ = "tipos_persona"

class TipoTransmision(CatalogoBase):
    __tablename__ = "tipos_transmision"

class TipoVia(CatalogoBase):
    __tablename__ = "tipos_via"
