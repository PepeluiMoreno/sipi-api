# models/agentes.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey
from app.db.base import Base
from app.db.mixins import (
    UUIDPKMixin, 
    AuditMixin, 
    IdentificacionMixin, 
    ContactoDireccionMixin, 
    TitularidadMixin
)

# ✅ Imports solo para TYPE CHECKING (anotaciones)
if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .catalogos import TipoPersona, RolTecnico
    from .transmisiones import Transmision, Inmatriculacion, TransmisionAnunciante
    from .actuaciones import ActuacionTecnico
    from .geografia import Localidad, ComunidadAutonoma

# ============================================================================
# BASES COMUNES
# ============================================================================

class PersonaMixin(IdentificacionMixin):
    """Base para personas físicas y jurídicas"""
    tipo_persona_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_persona.id"), index=True)

class TitularBase(UUIDPKMixin, AuditMixin, Base):
    """Base para tablas de titulares temporales"""
    __abstract__ = True
    
    fecha_inicio: Mapped[datetime] = mapped_column(index=True)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(index=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(100))

# ============================================================================
# AGENTES PERSONAS
# ============================================================================

class Adquiriente(UUIDPKMixin, AuditMixin, PersonaMixin, ContactoDireccionMixin, Base):
    """Persona que adquiere un inmueble en una transmisión"""
    __tablename__ = "adquirientes"
    
    # Relaciones
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="adquiriente")

class Transmitente(UUIDPKMixin, AuditMixin, PersonaMixin, ContactoDireccionMixin, Base):
    """Persona que transmite un inmueble"""
    __tablename__ = "transmitentes"
    
    # Relaciones
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="transmitente")

class Tecnico(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, Base):
    """Técnico profesional (arquitecto, ingeniero, etc.)"""
    __tablename__ = "tecnicos"
    
    rol_tecnico_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("roles_tecnico.id"), index=True)
    colegio_profesional_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("colegios_profesionales.id"), index=True)
    numero_colegiado: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    fecha_colegiacion: Mapped[Optional[datetime]] = mapped_column()
    
    # Relaciones
    rol_tecnico: Mapped[Optional["RolTecnico"]] = relationship("RolTecnico", back_populates="tecnicos")
    colegio_profesional: Mapped[Optional["ColegioProfesional"]] = relationship("ColegioProfesional", back_populates="tecnicos")
    actuaciones: Mapped[list["ActuacionTecnico"]] = relationship("ActuacionTecnico", back_populates="tecnico")

# ============================================================================
# ADMINISTRACIONES Y ORGANISMOS
# ============================================================================

class Administracion(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin["AdministracionTitular"], Base):
    """Administración pública (estatal, autonómica, local)"""
    __tablename__ = "administraciones"
    
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ambito: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Relaciones
    comunidad_autonoma: Mapped["ComunidadAutonoma"] = relationship("ComunidadAutonoma", back_populates="administraciones")

class AdministracionTitular(TitularBase):
    """Responsable de una administración"""
    __tablename__ = "administraciones_titulares"
    
    administracion_id: Mapped[str] = mapped_column(String(36), ForeignKey("administraciones.id"), index=True)
    
    # Relaciones
    administracion: Mapped["Administracion"] = relationship("Administracion", back_populates="titulares")

class ColegioProfesional(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, Base):
    """Colegio profesional de arquitectos, ingenieros, etc."""
    __tablename__ = "colegios_profesionales"
    
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    codigo: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    
    # Relaciones
    tecnicos: Mapped[list["Tecnico"]] = relationship("Tecnico", back_populates="colegio_profesional")

# ============================================================================
# ENTIDADES ECLESIÁSTICAS
# ============================================================================

class Diocesis(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin["DiocesisTitular"], Base):
    """Diócesis católica"""
    __tablename__ = "diocesis"
    
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    wikidata_qid: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    
    # Relaciones
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="diocesis")

class DiocesisTitular(TitularBase):
    """Obispo de una diócesis"""
    __tablename__ = "diocesis_titulares"
    
    diocesis_id: Mapped[str] = mapped_column(String(36), ForeignKey("diocesis.id"), index=True)
    
    # Relaciones
    diocesis: Mapped["Diocesis"] = relationship("Diocesis", back_populates="titulares")

# ============================================================================
# ENTIDADES REGISTRALES Y NOTARIALES
# ============================================================================

class Notaria(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin["NotariaTitular"], Base):
    """Notaría"""
    __tablename__ = "notarias"
    
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    
    # Relaciones
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="notaria")
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="notarias")

class NotariaTitular(TitularBase):
    """Notario titular de una notaría"""
    __tablename__ = "notarias_titulares"
    
    notaria_id: Mapped[str] = mapped_column(String(36), ForeignKey("notarias.id"), index=True)
    
    # Relaciones
    notaria: Mapped["Notaria"] = relationship("Notaria", back_populates="titulares")

class RegistroPropiedad(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, TitularidadMixin["RegistroPropiedadTitular"], Base):
    __tablename__ = 'registros_propiedad'
    
    localidad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("localidades.id"), index=True)
    
    # Relaciones
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="registros_propiedad")
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="registro_propiedad")
    inmatriculaciones: Mapped[list["Inmatriculacion"]] = relationship("Inmatriculacion", back_populates="registro_propiedad")

class RegistroPropiedadTitular(TitularBase):  # ✅ Cambiar nombre
    __tablename__ = "registros_titulares"  # La tabla puede seguir llamándose igual
    
    registro_propiedad_id: Mapped[str] = mapped_column(String(36), ForeignKey("registros_propiedad.id"), index=True)
    
    # Relaciones
    registro_propiedad: Mapped["RegistroPropiedad"] = relationship("RegistroPropiedad", back_populates="titulares")

# ============================================================================
# ENTIDADES COMERCIALES
# ============================================================================

class AgenciaInmobiliaria(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, Base):
    """Agencia inmobiliaria"""
    __tablename__ = "agencias_inmobiliarias"
    
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    
    # Relaciones
    transmisiones_anunciadas: Mapped[list["TransmisionAnunciante"]] = relationship("TransmisionAnunciante", back_populates="agencia_inmobiliaria")
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="agencias_inmobiliarias")