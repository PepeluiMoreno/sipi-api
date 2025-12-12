# models/geografia.py

from __future__ import annotations
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Boolean, ForeignKey, Index

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

class ComunidadAutonoma(UUIDPKMixin, AuditMixin, Base):
    """Comunidad Autónoma de España"""
    __tablename__ = "comunidades_autonomas"
    __table_args__ = 
    codigo: Mapped[str] = mapped_column(String(2), unique=True, index=True, nullable=False)
    codigo_ine: Mapped[str] = mapped_column(String(2), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    nombre_oficial: Mapped[str] = mapped_column(String(150), nullable=False)
    capital: Mapped[Optional[str]] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    
    # Relaciones
    provincias: Mapped[list["Provincia"]] = relationship("Provincia", back_populates="comunidad_autonoma", cascade="all, delete-orphan")
    municipios: Mapped[list["Municipio"]] = relationship("Municipio", back_populates="comunidad_autonoma")
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="comunidad_autonoma")
    figuras_proteccion: Mapped[list["FiguraProteccion"]] = relationship("FiguraProteccion", back_populates="comunidad_autonoma")
    administraciones: Mapped[list["Administracion"]] = relationship("Administracion", back_populates="comunidad_autonoma")
    
    __table_args__ = (
        Index('ix_ccaa_codigo', 'codigo'),
        Index('ix_ccaa_codigo_ine', 'codigo_ine'),
        Index('ix_ccaa_nombre', 'nombre'),
        Index('ix_ccaa_activo', 'activo'),
        {'schema': 'sipi'}
    )
    
    def __repr__(self) -> str:
        return f"<ComunidadAutonoma {self.codigo} - {self.nombre}>"


class Provincia(UUIDPKMixin, AuditMixin, Base):
    """Provincia española"""
    __tablename__ = "provincias"
    
    codigo: Mapped[str] = mapped_column(String(2), unique=True, index=True, nullable=False)
    codigo_iso: Mapped[str] = mapped_column(String(3), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    nombre_oficial: Mapped[Optional[str]] = mapped_column(String(150))
    capital: Mapped[Optional[str]] = mapped_column(String(100))
    comunidad_autonoma_id: Mapped[str] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Relaciones
    comunidad_autonoma: Mapped["ComunidadAutonoma"] = relationship("ComunidadAutonoma", back_populates="provincias")
    municipios: Mapped[list["Municipio"]] = relationship("Municipio", back_populates="provincia", cascade="all, delete-orphan")
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="provincia")
    administraciones: Mapped[list["Administracion"]] = relationship("Administracion", back_populates="provincia")
    
    __table_args__ = (
        Index('ix_provincia_codigo', 'codigo'),
        Index('ix_provincia_codigo_iso', 'codigo_iso'),
        Index('ix_provincia_nombre', 'nombre'),
        Index('ix_provincia_ccaa', 'comunidad_autonoma_id'),
        Index('ix_provincia_activo', 'activo'),
        {'schema': 'sipi'}
    )
    
    def __repr__(self) -> str:
        return f"<Provincia {self.codigo_iso} - {self.nombre}>"


class Municipio(UUIDPKMixin, AuditMixin, Base):
        __table_args__ = {'schema': 'sipi'}
    """Municipio español"""
    __tablename__ = "municipios"
    
    codigo_ine: Mapped[str] = mapped_column(String(5), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    nombre_oficial: Mapped[Optional[str]] = mapped_column(String(200))
    provincia_id: Mapped[str] = mapped_column(String(36), ForeignKey("provincias.id"), index=True, nullable=False)
    comunidad_autonoma_id: Mapped[str] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Relaciones
    provincia: Mapped["Provincia"] = relationship("Provincia", back_populates="municipios")
    comunidad_autonoma: Mapped["ComunidadAutonoma"] = relationship("ComunidadAutonoma", back_populates="municipios")
    
    # Relaciones 1:M con nombres descriptivos específicos
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="municipio")
    administraciones: Mapped[list["Administracion"]] = relationship("Administracion", back_populates="municipio_sede")
    adquirientes: Mapped[list["Adquiriente"]] = relationship("Adquiriente", back_populates="municipio_residencia")
    transmitentes: Mapped[list["Transmitente"]] = relationship("Transmitente", back_populates="municipio_residencia")
    tecnicos: Mapped[list["Tecnico"]] = relationship("Tecnico", back_populates="municipio_trabajo")
    notarias: Mapped[list["Notaria"]] = relationship("Notaria", back_populates="municipio_ubicacion")
    registros_propiedad: Mapped[list["RegistroPropiedad"]] = relationship("RegistroPropiedad", back_populates="municipio_ubicacion")
    colegios_profesionales: Mapped[list["ColegioProfesional"]] = relationship("ColegioProfesional", back_populates="municipio_sede")
    agencias_inmobiliarias: Mapped[list["AgenciaInmobiliaria"]] = relationship("AgenciaInmobiliaria", back_populates="municipio_oficina")
    diocesis: Mapped[list["Diocesis"]] = relationship("Diocesis", back_populates="municipio_sede")
    
    def __repr__(self) -> str:
        return f"<Municipio {self.codigo_ine} - {self.nombre}>"