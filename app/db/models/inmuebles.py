from __future__ import annotations
from datetime import datetime
from typing import Optional, List
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Numeric, Boolean, ForeignKey
from geoalchemy2 import Geometry

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin


class Inmueble(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles"
    
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True)
    provincia_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    municipio_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("municipios.id"), index=True)
    direccion: Mapped[Optional[str]] = mapped_column(String(500))
    coordenadas: Mapped[Optional[Geometry]] = mapped_column(Geometry(geometry_type='POINT', srid=4326))
    
    tipo_inmueble_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_inmueble.id"), index=True)
    figura_proteccion_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_figura_proteccion.id"), index=True)
    estado_conservacion_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("estados_conservacion.id"), index=True)
    estado_tratamiento_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("estados_tratamiento.id"), index=True)
    
    diocesis_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("diocesis.id"), index=True)
    
    superficie_construida: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    superficie_parcela: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    num_plantas: Mapped[Optional[int]]
    ano_construccion: Mapped[Optional[int]]
    
    valor_catastral: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    valor_mercado: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    
    # Relaciones
    comunidad_autonoma: Mapped[Optional["ComunidadAutonoma"]] = relationship("ComunidadAutonoma", back_populates="inmuebles")
    provincia: Mapped[Optional["Provincia"]] = relationship("Provincia", back_populates="inmuebles")
    municipio: Mapped[Optional["Municipio"]] = relationship("Municipio", back_populates="inmuebles")
    tipo_inmueble: Mapped[Optional["TipoInmueble"]] = relationship("TipoInmueble", back_populates="inmuebles")
    figura_proteccion: Mapped[Optional["FiguraProteccion"]] = relationship("FiguraProteccion", back_populates="inmuebles")
    estado_conservacion: Mapped[Optional["TipoEstadoConservacion"]] = relationship("TipoEstadoConservacion", back_populates="inmuebles")
    estado_tratamiento: Mapped[Optional["TipoEstadoTratamiento"]] = relationship("TipoEstadoTratamiento", back_populates="inmuebles")
    diocesis: Mapped[Optional["Diocesis"]] = relationship("Diocesis", back_populates="inmuebles")
    
    denominaciones: Mapped[List["InmuebleDenominacion"]] = relationship("InmuebleDenominacion", back_populates="inmueble", cascade="all, delete-orphan")
    inmatriculaciones: Mapped[List["Inmatriculacion"]] = relationship("Inmatriculacion", back_populates="inmueble", cascade="all, delete-orphan")
    osm_ext: Mapped[List["InmuebleOSMExt"]] = relationship("InmuebleOSMExt", back_populates="inmueble", cascade="all, delete-orphan")
    wd_ext: Mapped[List["InmuebleWDExt"]] = relationship("InmuebleWDExt", back_populates="inmueble", cascade="all, delete-orphan")
    citas: Mapped[List["InmuebleCita"]] = relationship("InmuebleCita", back_populates="inmueble", cascade="all, delete-orphan")
    
    documentos: Mapped[List["InmuebleDocumento"]] = relationship("InmuebleDocumento", back_populates="inmueble", cascade="all, delete-orphan")
    actuaciones: Mapped[List["Actuacion"]] = relationship("Actuacion", back_populates="inmueble", cascade="all, delete-orphan")
    transmisiones: Mapped[List["Transmision"]] = relationship("Transmision", back_populates="inmueble", cascade="all, delete-orphan")


class Inmatriculacion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmatriculaciones"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    registro_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("registros_propiedad.id"), index=True)
    tipo_certificacion_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_certificacion_propiedad.id"), index=True)
    
    fecha_inmatriculacion: Mapped[Optional[datetime]]
    numero_finca: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    tomo: Mapped[Optional[str]] = mapped_column(String(50))
    libro: Mapped[Optional[str]] = mapped_column(String(50))
    folio: Mapped[Optional[str]] = mapped_column(String(50))
    inscripcion: Mapped[Optional[str]] = mapped_column(String(50))
    observaciones: Mapped[Optional[str]] = mapped_column(Text)
    
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="inmatriculaciones")
    registro_propiedad: Mapped[Optional["RegistroPropiedad"]] = relationship("RegistroPropiedad", back_populates="inmatriculaciones")
    tipo_certificacion_propiedad: Mapped[Optional["TipoCertificacionPropiedad"]] = relationship("TipoCertificacionPropiedad", back_populates="inmatriculaciones")


class InmuebleDenominacion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_denominaciones"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    denominacion: Mapped[str] = mapped_column(String(255), index=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False)
    
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="denominaciones")


class InmuebleOSMExt(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_osm_ext"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    osm_type: Mapped[str] = mapped_column(String(10))
    osm_id: Mapped[str] = mapped_column(String(50), index=True)
    osm_tags: Mapped[Optional[str]] = mapped_column(Text)
    
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="osm_ext")


class InmuebleWDExt(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_wd_ext"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    wikidata_qid: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    wikipedia_url: Mapped[Optional[str]] = mapped_column(String(500))
    
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="wd_ext")


class InmuebleCita(UUIDPKMixin, AuditMixin, Base):
    """Cita bibliografica de un inmueble en una fuente"""
    __tablename__ = "citas_bibliograficas"

    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    fuente_id: Mapped[str] = mapped_column(String(36), ForeignKey("fuentes_historiograficas.id"), index=True)
    referencia: Mapped[str] = mapped_column(String(500))
    pagina: Mapped[Optional[str]] = mapped_column(String(50))
    fecha: Mapped[Optional[datetime]]
    
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="citas")
    fuente: Mapped["FuenteHistoriografica"] = relationship("FuenteHistoriografica", back_populates="citas_bibliograficas")