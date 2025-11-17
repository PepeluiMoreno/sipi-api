# models/agentes.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey

if TYPE_CHECKING:
    from app.db.base import Base
    from app.db.mixins import UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, TitularidadMixin
)   from .inmuebles import Inmueble
    from .catalogos import TipoPersona, RolTecnico
    from .transmisiones import Transmision, Inmatriculacion
    from .actuaciones import ActuacionTecnico
    from .geografia import Localidad, ComunidadAutonoma

# BASES COMUNES
class PersonaMixin(IdentificacionMixin):
    """Base para personas físicas y jurídicas"""
    tipo_persona_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_persona.id"), index=True)

class TitularBase(UUIDPKMixin, AuditMixin, Base):
    """Base para tablas de titulares temporales"""
    __abstract__ = True
    
    fecha_inicio: Mapped[datetime] = mapped_column(index=True)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(index=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(100))

# MODELOS ESPECÍFICOS
class Adquiriente(UUIDPKMixin, AuditMixin, PersonaMixin, ContactoDireccionMixin, Base):
    __tablename__ = "adquirientes"
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="adquiriente")

class Administracion(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin["AdministracionTitular"], Base):
    __tablename__ = "administraciones"
    
    DENOMINACION_TITULARIDAD = "titular_administracion"
    
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ambito: Mapped[Optional[str]] = mapped_column(String(100))
    
    comunidad_autonoma: Mapped["ComunidadAutonoma"] = relationship("ComunidadAutonoma", back_populates="administraciones")

class AdministracionTitular(TitularBase):
    __tablename__ = "administraciones_titulares"
    
    administracion_id: Mapped[str] = mapped_column(String(36), ForeignKey("administraciones.id"), index=True)
    administracion: Mapped["Administracion"] = relationship("Administracion", back_populates="titulares")

class AgenciaInmobiliaria(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, Base):
    __tablename__ = "agencias_inmobiliarias"
    
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    
    # Relaciones
    transmisiones_anunciadas: Mapped[list["TransmisionAnunciante"]] = relationship("TransmisionAnunciante", back_populates="agencia_inmobiliaria")
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="agencias_inmobiliarias")

class ColegioProfesional(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, Base):
    __tablename__ = "colegios_profesionales"
    
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    codigo: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    
    tecnicos: Mapped[list["Tecnico"]] = relationship("Tecnico", back_populates="colegio_profesional")

class Diocesis(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin["DiocesisTitular"], Base):
    __tablename__ = "diocesis"
    
    DENOMINACION_TITULARIDAD = "obispo"
    
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    wikidata_qid: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    
    # Relaciones
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="diocesis")

class DiocesisTitular(TitularBase):
    __tablename__ = "diocesis_titulares"
    
    diocesis_id: Mapped[str] = mapped_column(String(36), ForeignKey("diocesis.id"), index=True)
    diocesis: Mapped["Diocesis"] = relationship("Diocesis", back_populates="titulares")

class Notaria(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin["NotariaTitular"], Base):
    __tablename__ = "notarias"
    
    DENOMINACION_TITULARIDAD = "notario"
    
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    
    # Relaciones
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="notaria")
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="notarias")

class NotariaTitular(TitularBase):
    __tablename__ = "notarias_titulares"
    
    notaria_id: Mapped[str] = mapped_column(String(36), ForeignKey("notarias.id"), index=True)
    notaria: Mapped["Notaria"] = relationship("Notaria", back_populates="titulares")

class Tecnico(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, Base):
    __tablename__ = "tecnicos"
    
    rol_tecnico_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("roles_tecnico.id"), index=True)
    colegio_profesional_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("colegios_profesionales.id"), index=True)
    numero_colegiado: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    fecha_colegiacion: Mapped[Optional[datetime]] = mapped_column()
    
    # Relaciones
    rol_tecnico: Mapped[Optional["RolTecnico"]] = relationship("RolTecnico", back_populates="tecnicos")
    colegio_profesional: Mapped[Optional["ColegioProfesional"]] = relationship("ColegioProfesional", back_populates="tecnicos")
    actuaciones: Mapped[list["ActuacionTecnico"]] = relationship("ActuacionTecnico", back_populates="tecnico")

class RegistroPropiedad(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, TitularidadMixin["RegistroTitular"], Base):
    __tablename__ = 'registros_propiedad'
    
    DENOMINACION_TITULARIDAD = "registrador"
    
    localidad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("localidades.id"), index=True)
    
    # Relaciones
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="registros_propiedad")

class RegistroTitular(TitularBase):
    __tablename__ = "registros_titulares"
    
    registro_propiedad_id: Mapped[str] = mapped_column(String(36), ForeignKey("registros_propiedad.id"), index=True)
    registro_propiedad: Mapped["RegistroPropiedad"] = relationship("RegistroPropiedad", back_populates="titulares")

class Transmitente(UUIDPKMixin, AuditMixin, PersonaMixin, ContactoDireccionMixin, Base):
    __tablename__ = "transmitentes"
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="transmitente")
