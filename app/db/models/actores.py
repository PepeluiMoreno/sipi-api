# models/actores.py
# Personas físicas o jurídicas intervinientes en los procesos del dominio

from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from sqlalchemy import String, ForeignKey

from app.db.base import Base
from app.db.mixins import (
    UUIDPKMixin, 
    AuditMixin, 
    IdentificacionMixin, 
    ContactoDireccionMixin, 
    TitularidadMixin
)

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
# ACTORES PERSONAS
# ============================================================================

class Adquiriente(UUIDPKMixin, AuditMixin, PersonaMixin, ContactoDireccionMixin, Base):
    """Persona que adquiere un inmueble en una transmisión"""
    __tablename__ = "adquirientes"
    
    # Relación con nombre descriptivo - residencia del adquiriente
    municipio_residencia: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(Adquiriente.municipio_id) == Municipio.id",
        back_populates="adquirientes"
    )
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="adquiriente")

class Transmitente(UUIDPKMixin, AuditMixin, PersonaMixin, ContactoDireccionMixin, Base):
    """Persona que transmite un inmueble"""
    __tablename__ = "transmitentes"
    
    # Relación con nombre descriptivo - residencia del transmitente
    municipio_residencia: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(Transmitente.municipio_id) == Municipio.id",
        back_populates="transmitentes"
    )
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="transmitente")

class Tecnico(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, Base):
    """Técnico profesional (arquitecto, ingeniero, etc.)"""
    __tablename__ = "tecnicos"
    
    # Foreign Keys adicionales (municipio_id viene del mixin)
    rol_tecnico_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("roles_tecnico.id"), index=True)
    colegio_profesional_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("colegios_profesionales.id"), index=True)
    
    # Campos adicionales
    numero_colegiado: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    fecha_colegiacion: Mapped[Optional[datetime]] = mapped_column()
    
    # Relaciones con nombres descriptivos
    rol_tecnico: Mapped[Optional["TipoRolTecnico"]] = relationship("TipoRolTecnico", back_populates="tecnicos")
    colegio_profesional: Mapped[Optional["ColegioProfesional"]] = relationship("ColegioProfesional", back_populates="tecnicos")
    municipio_trabajo: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(Tecnico.municipio_id) == Municipio.id",
        back_populates="tecnicos"
    )
    actuaciones: Mapped[list["ActuacionTecnico"]] = relationship("ActuacionTecnico", back_populates="tecnico")

# ============================================================================
# ADMINISTRACIONES Y ORGANISMOS
# ============================================================================

class Administracion(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin, Base):
    """Administración pública (estatal, autonómica, local)"""
    __tablename__ = "administraciones"
    
    nombre: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ambito: Mapped[Optional[str]] = mapped_column(String(100))
    
    # FKs geográficos vienen del DireccionMixin (comunidad_autonoma_id, provincia_id, municipio_id)
    
    # Relaciones con nombres descriptivos y primaryjoin explícito
    comunidad_autonoma: Mapped[Optional["ComunidadAutonoma"]] = relationship(
        "ComunidadAutonoma", 
        primaryjoin="foreign(Administracion.comunidad_autonoma_id) == ComunidadAutonoma.id",
        back_populates="administraciones"
    )
    provincia: Mapped[Optional["Provincia"]] = relationship(
        "Provincia",
        primaryjoin="foreign(Administracion.provincia_id) == Provincia.id",
        back_populates="administraciones"
    )
    municipio_sede: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(Administracion.municipio_id) == Municipio.id",
        back_populates="administraciones"
    )
    titulares: Mapped[list["AdministracionTitular"]] = relationship("AdministracionTitular", back_populates="administracion", cascade="all, delete-orphan")
    subvenciones: Mapped[list["SubvencionAdministracion"]] = relationship("SubvencionAdministracion", back_populates="administracion")

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
    
    # Relaciones con nombres descriptivos
    municipio_sede: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(ColegioProfesional.municipio_id) == Municipio.id",
        back_populates="colegios_profesionales"
    )
    tecnicos: Mapped[list["Tecnico"]] = relationship("Tecnico", back_populates="colegio_profesional")

# ============================================================================
# ENTIDADES ECLESIÁSTICAS
# ============================================================================

class Diocesis(UUIDPKMixin, AuditMixin, ContactoDireccionMixin, TitularidadMixin, Base):
    """Diócesis católica"""
    __tablename__ = "diocesis"
    
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    wikidata_qid: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    
    # Relaciones con nombres descriptivos - sede diocesana
    municipio_sede: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(Diocesis.municipio_id) == Municipio.id",
        back_populates="diocesis"
    )
    inmuebles: Mapped[list["Inmueble"]] = relationship("Inmueble", back_populates="diocesis")
    titulares: Mapped[list["DiocesisTitular"]] = relationship("DiocesisTitular", back_populates="diocesis", cascade="all, delete-orphan")

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
    
    # Relaciones con nombres descriptivos - ubicación física de la notaría
    municipio_ubicacion: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(Notaria.municipio_id) == Municipio.id",
        back_populates="notarias"
    )
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="notaria")
    titulares: Mapped[list["NotariaTitular"]] = relationship("NotariaTitular", back_populates="notaria", cascade="all, delete-orphan")

class NotariaTitular(TitularBase):
    """Notario titular"""
    __tablename__ = "notarias_titulares"
    
    notaria_id: Mapped[str] = mapped_column(String(36), ForeignKey("notarias.id"), index=True)
    
    # Relaciones
    notaria: Mapped["Notaria"] = relationship("Notaria", back_populates="titulares")

class RegistroPropiedad(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoDireccionMixin, TitularidadMixin, Base):
    """Registro de la Propiedad"""
    __tablename__ = "registros_propiedad"
    
    # Relaciones con nombres descriptivos - ubicación del registro
    municipio_ubicacion: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(RegistroPropiedad.municipio_id) == Municipio.id",
        back_populates="registros_propiedad"
    )
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="registro_propiedad")
    inmatriculaciones: Mapped[list["Inmatriculacion"]] = relationship("Inmatriculacion", back_populates="registro_propiedad")
    titulares: Mapped[list["RegistroPropiedadTitular"]] = relationship("RegistroPropiedadTitular", back_populates="registro_propiedad", cascade="all, delete-orphan")

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
    
    # Relaciones con nombres descriptivos - oficina de la agencia
    municipio_oficina: Mapped[Optional["Municipio"]] = relationship(
        "Municipio", 
        primaryjoin="foreign(AgenciaInmobiliaria.municipio_id) == Municipio.id",
        back_populates="agencias_inmobiliarias"
    )
    transmisiones_anunciadas: Mapped[list["TransmisionAnunciante"]] = relationship("TransmisionAnunciante", back_populates="agencia_inmobiliaria")