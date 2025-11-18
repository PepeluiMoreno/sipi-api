# models/inmuebles.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
import enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, ForeignKey, Numeric, DateTime, Enum
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
import strawberry

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .geografia import Localidad, Provincia, ComunidadAutonoma
    from .agentes import Diocesis
    from .catalogos import TipoInmueble, EstadoConservacion, EstadoTratamiento, TipoVia, TipoDenominacion
    from .transmisiones import Transmision, Inmatriculacion
    from .actuaciones import Actuacion
    from .documentos import InmuebleDocumento
    from .historiografia import CitaHistoriografica
    from .proteccion import InmuebleFiguraProteccion

# ============================================================================
# ENUMS
# ============================================================================

@strawberry.enum
class IdiomaInmueble(str, enum.Enum):
    """Idiomas para denominaciones de inmuebles (ISO 639-1)"""
    CASTELLANO = "es"
    CATALAN = "ca"
    GALLEGO = "gl"
    EUSKERA = "eu"
    OCCITANO = "oc"  # Aranés
    LATIN = "la"
    ARAGONES = "an"
    ASTURIANO = "ast"
    PORTUGUES = "pt"
    FRANCES = "fr"
    INGLES = "en"

# ============================================================================
# MODELOS
# ============================================================================

class Inmueble(UUIDPKMixin, AuditMixin, Base):
    """Modelo principal de inmuebles patrimoniales"""
    __tablename__ = "inmuebles"
    
    # Identificación
    nombre: Mapped[Optional[str]] = mapped_column(String(255), index=True)  # Denominación principal (legacy)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    
    # Dirección (normalizada y geocodificada)
    direccion_normalizada: Mapped[Optional[str]] = mapped_column(Text)
    latitud: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 8))
    longitud: Mapped[Optional[Decimal]] = mapped_column(Numeric(11, 8))
    
    # Jerarquía geográfica
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True)
    provincia_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    localidad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("localidades.id"), index=True)
    diocesis_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("diocesis.id"), index=True)
    
    # Características
    tipo_inmueble_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_inmueble.id"), index=True)
    estado_conservacion_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("estados_conservacion.id"), index=True)
    estado_tratamiento_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("estados_tratamiento.id"), index=True)
    
    # Estados
    es_bic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    es_ruina: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    esta_inmatriculado: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Relaciones principales
    comunidad_autonoma: Mapped[Optional["ComunidadAutonoma"]] = relationship("ComunidadAutonoma", back_populates="inmuebles", lazy="joined")
    provincia: Mapped[Optional["Provincia"]] = relationship("Provincia", back_populates="inmuebles", lazy="joined")
    localidad: Mapped[Optional["Localidad"]] = relationship("Localidad", back_populates="inmuebles", lazy="joined")
    diocesis: Mapped[Optional["Diocesis"]] = relationship("Diocesis", back_populates="inmuebles")
    tipo_inmueble: Mapped[Optional["TipoInmueble"]] = relationship("TipoInmueble", back_populates="inmuebles")
    estado_conservacion: Mapped[Optional["EstadoConservacion"]] = relationship("EstadoConservacion", back_populates="inmuebles")
    estado_tratamiento: Mapped[Optional["EstadoTratamiento"]] = relationship("EstadoTratamiento", back_populates="inmuebles")
    
    # Relaciones 1:N
    denominaciones: Mapped[list["InmuebleDenominacion"]] = relationship("InmuebleDenominacion", back_populates="inmueble", cascade="all, delete-orphan")
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="inmueble", cascade="all, delete-orphan")
    actuaciones: Mapped[list["Actuacion"]] = relationship("Actuacion", back_populates="inmueble", cascade="all, delete-orphan")
    documentos: Mapped[list["InmuebleDocumento"]] = relationship("InmuebleDocumento", back_populates="inmueble", cascade="all, delete-orphan")
    citas_historiograficas: Mapped[list["CitaHistoriografica"]] = relationship("CitaHistoriografica", back_populates="inmueble", cascade="all, delete-orphan")
    figuras_proteccion: Mapped[list["InmuebleFiguraProteccion"]] = relationship("InmuebleFiguraProteccion", back_populates="inmueble", cascade="all, delete-orphan")
    
    # Relaciones 1:1
    inmatriculacion: Mapped[Optional["Inmatriculacion"]] = relationship("Inmatriculacion", back_populates="inmueble", uselist=False, cascade="all, delete-orphan")
    osm_ext: Mapped[Optional["InmuebleOSMExt"]] = relationship("InmuebleOSMExt", back_populates="inmueble", uselist=False, cascade="all, delete-orphan")
    wd_ext: Mapped[Optional["InmuebleWDExt"]] = relationship("InmuebleWDExt", back_populates="inmueble", uselist=False, cascade="all, delete-orphan")
    
    # Propiedades calculadas
    @property
    def denominacion_principal(self) -> Optional[str]:
        """Obtiene la denominación marcada como principal"""
        principal = next((d for d in self.denominaciones if d.es_principal), None)
        return principal.denominacion if principal else self.nombre
    
    @property
    def denominaciones_alternativas(self) -> list["InmuebleDenominacion"]:
        """Obtiene todas las denominaciones que no son principales"""
        return [d for d in self.denominaciones if not d.es_principal]


class InmuebleDenominacion(UUIDPKMixin, AuditMixin, Base):
    """Denominaciones múltiples de un inmueble"""
    __tablename__ = "inmuebles_denominaciones"
    
    # Relación con inmueble
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    
    # Denominación
    denominacion: Mapped[str] = mapped_column(String(500), index=True)
    tipo_denominacion_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_denominacion.id"), index=True)
    
    # Características
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    idioma: Mapped[Optional[IdiomaInmueble]] = mapped_column(Enum(IdiomaInmueble), index=True)
    
    # Vigencia temporal
    fecha_inicio: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadatos
    fuente: Mapped[Optional[str]] = mapped_column(String(255))  # BIC, Catastro, OSM, Wikidata, etc.
    notas: Mapped[Optional[str]] = mapped_column(Text)
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="denominaciones")
    tipo_denominacion: Mapped[Optional["TipoDenominacion"]] = relationship("TipoDenominacion", back_populates="inmuebles_denominaciones")
    
    @property
    def esta_vigente(self) -> bool:
        """Verifica si la denominación está actualmente vigente"""
        ahora = datetime.now()
        if self.fecha_inicio and ahora < self.fecha_inicio:
            return False
        if self.fecha_fin and ahora > self.fecha_fin:
            return False
        return True


class InmuebleOSMExt(UUIDPKMixin, AuditMixin, Base):
    """Datos extendidos de OpenStreetMap"""
    __tablename__ = "inmuebles_osm_ext"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), unique=True, index=True)
    osm_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    osm_type: Mapped[Optional[str]] = mapped_column(String(10))
    version: Mapped[Optional[int]] = mapped_column()
    name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    
    # Datos específicos
    denomination: Mapped[Optional[str]] = mapped_column(String(255))
    diocese: Mapped[Optional[str]] = mapped_column(String(255))
    operator: Mapped[Optional[str]] = mapped_column(String(255))
    heritage_status: Mapped[Optional[str]] = mapped_column(String(100))
    historic: Mapped[Optional[str]] = mapped_column(String(100))
    ruins: Mapped[bool] = mapped_column(Boolean, default=False)
    has_polygon: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Geometría
    geom: Mapped[Optional[Geometry]] = mapped_column(Geometry('POINT', srid=4326))
    
    # Dirección OSM
    address_street: Mapped[Optional[str]] = mapped_column(String(255))
    address_city: Mapped[Optional[str]] = mapped_column(String(100))
    address_postcode: Mapped[Optional[str]] = mapped_column(String(10))
    
    # Metadatos
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)
    qa_flags: Mapped[Optional[dict]] = mapped_column(JSONB)
    source_refs: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Relación
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="osm_ext", uselist=False)


class InmuebleWDExt(UUIDPKMixin, AuditMixin, Base):
    """Datos extendidos de Wikidata"""
    __tablename__ = "inmuebles_wd_ext"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), unique=True, index=True)
    wikidata_qid: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    commons_category: Mapped[Optional[str]] = mapped_column(String(255))
    inception: Mapped[Optional[str]] = mapped_column(String(100))
    
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    claims: Mapped[Optional[dict]] = mapped_column(JSONB)
    sitelinks: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="wd_ext", uselist=False)