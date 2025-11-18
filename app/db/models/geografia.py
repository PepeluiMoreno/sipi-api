# models/geografia.py
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .agentes import Notaria, RegistroPropiedad, Administracion, AgenciaInmobiliaria
    from .inmuebles import Inmueble

class ComunidadAutonoma(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "comunidades_autonomas"
    
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    
    # Relaciones
    provincias: Mapped[list["Provincia"]] = relationship("Provincia", back_populates="comunidad_autonoma", cascade="all, delete-orphan")
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="comunidad_autonoma")
    administraciones: Mapped[list["Administracion"]] = relationship("Administracion", back_populates="comunidad_autonoma")

class Provincia(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "provincias"
    
    nombre: Mapped[str] = mapped_column(String(100), index=True)
    comunidad_autonoma_id: Mapped[str] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True)
    
    # Relaciones
    comunidad_autonoma: Mapped["ComunidadAutonoma"] = relationship("ComunidadAutonoma", back_populates="provincias")
    localidades: Mapped[list["Localidad"]] = relationship("Localidad", back_populates="provincia", cascade="all, delete-orphan")
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="provincia")
    administraciones: Mapped[list["Administracion"]] = relationship("Administracion", back_populates="provincia")  # ✅ AÑADIDA

class Localidad(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "localidades"
    
    nombre: Mapped[str] = mapped_column(String(100), index=True)
    provincia_id: Mapped[str] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    
    # Relaciones
    provincia: Mapped["Provincia"] = relationship("Provincia", back_populates="localidades")
    notarias: Mapped[list["Notaria"]] = relationship("Notaria", back_populates="localidad")
    registros_propiedad: Mapped[list["RegistroPropiedad"]] = relationship("RegistroPropiedad", back_populates="localidad")
    agencias_inmobiliarias: Mapped[list["AgenciaInmobiliaria"]] = relationship("AgenciaInmobiliaria", back_populates="localidad")
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="localidad")
    administraciones: Mapped[list["Administracion"]] = relationship("Administracion", back_populates="localidad")  # ✅ AÑADIDA