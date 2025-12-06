# models/actores.py
#  Personas físicas o jurídicas intervinientes en los procesos del dominio

from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String,  ForeignKey

from app.db.base import Base
from app.db.mixins import (
    UUIDPKMixin, 
    AuditMixin, 
    IdentificacionMixin, 
    ContactoDireccionMixin, 
    TitularidadMixin
)

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .tipologias import TipoPersona, TipoRolTecnico
    from .transmisiones import Transmision, Inmatriculacion, TransmisionAnunciante
    from .actuaciones import ActuacionTecnico
    from .geografia import Localidad, ComunidadAutonoma, Provincia

# ============================================================================
# BASES COMUNES
# ============================================================================

class PersonaMixin(IdentificacionMixin):
    """Base para personas físicas y jurídicas"""
    tipo_persona_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_persona.id"), index=True)

class TitularBase(UUIDPKMixin, AuditMixin, IdentificacionMixin, Base):
    """Base para tablas de titulares temporales (personas físicas)"""
    __abstract__ = True
    
    fecha_inicio: Mapped[datetime] = mapped_column(index=True)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(index=True)
    cargo: Mapped[Optional[str]] = mapped_column(String(100))

# ============================================================================
# actores PERSONAS
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
    
    # Foreign Keys
    rol_tecnico_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("roles_tecnico.id"), index=True)
    colegio_profesional_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("colegios_profesionales.id"), index=True)
    
    # Campos adicionales
    numero_colegiado: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    fecha_colegiacion: Mapped[Optional[datetime]] = mapped_column()
    
    # Relaciones
    rol_tecnico: Mapped[Optional["TipoRolTecnico"]] = relationship("TipoRolTecnico", back_populates="tecnicos")
    colegio_profesional: Mapped[Optional["ColegioProfesional"]] = relationship("ColegioProfesional", back_populates="tecnicos")
    actuaciones: Mapped[list["ActuacionTecnico"]] = relationship("ActuacionTecnico", back_populates="tecnico")

# ============================================================================
# ADMINISTRACIONES Y ORGANISMOS
# ============================================================================

class Administracion(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin, Base):
    """Administración pública (estatal, autonómica, local)"""
    __tablename__ = "administraciones"
    
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ambito: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Foreign Keys
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True)
    provincia_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    localidad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("localidades.id"), index=True)
    
    # Relaciones
    comunidad_autonoma: Mapped[Optional["ComunidadAutonoma"]] = relationship("ComunidadAutonoma", back_populates="administraciones")
    provincia: Mapped[Optional["Provincia"]] = relationship("Provincia", back_populates="administraciones")
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="administraciones")

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

class Diocesis(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin, Base):
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

class Notaria(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, Base):
    """Notaría"""
    __tablename__ = "notarias"
    
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    
    # La relación localidad ya viene del mixin ContactoDireccionMixin
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="notaria")

class RegistroPropiedad(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, TitularidadMixin, Base):
    """Registro de la Propiedad"""
    __tablename__ = "registros_propiedad"
    
    # La relación localidad ya viene del mixin ContactoDireccionMixin
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="registro_propiedad")
    inmatriculaciones: Mapped[list["Inmatriculacion"]] = relationship("Inmatriculacion", back_populates="registro_propiedad")

class RegistroPropiedadTitular(TitularBase):
    """Registrador de la Propiedad (persona física titular del registro)"""
    __tablename__ = "registros_propiedad_titulares"
    
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
    
    # La relación localidad ya viene del mixin ContactoDireccionMixin
    transmisiones_anunciadas: Mapped[list["TransmisionAnunciante"]] = relationship("TransmisionAnunciante", back_populates="agencia_inmobiliaria")