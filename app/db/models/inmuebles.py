# models/inmuebles.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
import enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, ForeignKey, Numeric, DateTime, Date, Enum
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
import strawberry

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .geografia import Localidad, Provincia, ComunidadAutonoma
    from .actores import Diocesis, RegistroPropiedad
    from .tipologias import (
        TipoInmueble,
        TipoEstadoConservacion,
        TipoEstadoTratamiento,
        TipoFiguraProteccion
    )
    from .transmisiones import Transmision, Inmatriculacion
    from .actuaciones import Actuacion
    from .documentos import Documento, InmuebleDocumento
    from .historiografia import CitaHistoriografica

# ---------------------------------------------------------------------------
# ENUMS
# ---------------------------------------------------------------------------

@strawberry.enum
class IdiomaInmueble(str, enum.Enum):
    CASTELLANO = "es"
    CATALAN = "ca"
    GALLEGO = "gl"
    EUSKERA = "eu"
    OCCITANO = "oc"
    LATIN = "la"
    ARAGONES = "an"
    ASTURIANO = "ast"
    PORTUGUES = "pt"
    FRANCES = "fr"
    INGLES = "en"

# ---------------------------------------------------------------------------
# MODELOS
# ---------------------------------------------------------------------------

class Inmueble(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles"

    # --- identificación y ubicación ----------------------------------------
    nombre: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    direccion_normalizada: Mapped[Optional[str]] = mapped_column(Text)
    latitud: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 8))
    longitud: Mapped[Optional[Decimal]] = mapped_column(Numeric(11, 8))

    # --- jerarquía geográfica ----------------------------------------------
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("comunidades_autonomas.id"), index=True
    )
    provincia_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("provincias.id"), index=True
    )
    localidad_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("localidades.id"), index=True
    )
    diocesis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("diocesis.id"), index=True
    )

    # --- características técnicas ------------------------------------------
    tipo_inmueble_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("tipos_inmueble.id"), index=True
    )
    estado_conservacion_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("estados_conservacion.id"), index=True
    )
    estado_tratamiento_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("estados_tratamiento.id"), index=True
    )
    figura_proteccion_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("grados_proteccion.id"), index=True
    )

    # --- relaciones principales --------------------------------------------
    comunidad_autonoma: Mapped[Optional["ComunidadAutonoma"]] = relationship(
        "ComunidadAutonoma", back_populates="inmuebles", lazy="joined"
    )
    provincia: Mapped[Optional["Provincia"]] = relationship(
        "Provincia", back_populates="inmuebles", lazy="joined"
    )
    localidad: Mapped[Optional["Localidad"]] = relationship(
        "Localidad", back_populates="inmuebles", lazy="joined"
    )
    diocesis: Mapped[Optional["Diocesis"]] = relationship("Diocesis", back_populates="inmuebles")
    tipo_inmueble: Mapped[Optional["TipoInmueble"]] = relationship(
        "TipoInmueble", back_populates="inmuebles"
    )
    estado_conservacion: Mapped[Optional["TipoEstadoConservacion"]] = relationship(
        "TipoEstadoConservacion", back_populates="inmuebles"
    )
    estado_tratamiento: Mapped[Optional["TipoEstadoTratamiento"]] = relationship(
        "TipoEstadoTratamiento", back_populates="inmuebles"
    )
    figura_proteccion: Mapped[Optional["TipoFiguraProteccion"]] = relationship(
        "TipoFiguraraProteccion", back_populates="inmuebles"
    )

    # --- inmatriculación 1:1 ----------------------------------------------
    inmatriculacion: Mapped[Optional["InmuebleInmatriculacion"]] = relationship(
        "InmuebleInmatriculacion",
        back_populates="inmueble",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # --- relaciones 1:N ----------------------------------------------------
    denominaciones: Mapped[list["InmuebleDenominaciones"]] = relationship(
        "InmuebleDenominacion", back_populates="inmueble", cascade="all, delete-orphan"
    )
    transmisiones: Mapped[list["Transmision"]] = relationship(
        "Transmision", back_populates="inmueble", cascade="all, delete-orphan"
    )
    actuaciones: Mapped[list["Actuacion"]] = relationship(
        "Actuacion", back_populates="inmueble", cascade="all, delete-orphan"
    )
    documentos: Mapped[list["InmuebleDocumento"]] = relationship(
        "InmuebleDocumento", back_populates="inmueble", cascade="all, delete-orphan"
    )
    citas_historiograficas: Mapped[list["CitaHistoriografica"]] = relationship(
        "CitaHistoriografica", back_populates="inmueble", cascade="all, delete-orphan"
    )
 

    # --- relaciones 1:1 antiguas ------------------------------------------
    inmatriculacion_old: Mapped[Optional["Inmatriculacion"]] = relationship(
        "Inmatriculacion", back_populates="inmueble", uselist=False, cascade="all, delete-orphan"
    )
    osm_ext: Mapped[Optional["InmuebleOSMExt"]] = relationship(
        "InmuebleOSMExt", back_populates="inmueble", uselist=False, cascade="all, delete-orphan"
    )
    wd_ext: Mapped[Optional["InmuebleWDExt"]] = relationship(
        "InmuebleWDExt", back_populates="inmueble", uselist=False, cascade="all, delete-orphan"
    )

    # -----------------------------------------------------------------------
    # Propiedades calculadas
    # -----------------------------------------------------------------------
    @property
    def denominacion_principal(self) -> Optional[str]:
        principal = next((d for d in self.denominaciones if d.es_principal), None)
        return principal.denominacion if principal else self.nombre

    @property
    def tiene_denominaciones_alternativas(self) -> bool:
        return any(not d.es_principal for d in self.denominaciones)

    @property
    def denominaciones_alternativas_lista(self) -> list[str]:
        return [d.denominacion for d in self.denominaciones if not d.es_principal]

    
    @property
    def tiene_datos_osm(self) -> bool:
        return self.osm_ext is not None

    @property
    def tiene_datos_wikidata(self) -> bool:
        return self.wd_ext is not None

    @property
    def tiene_transmisiones(self) -> bool:
        return len(self.transmisiones) > 0

    @property
    def tiene_actuaciones(self) -> bool:
        return len(self.actuaciones) > 0

    @property
    def tiene_documentos(self) -> bool:
        return len(self.documentos) > 0

    @property
    def tiene_proteccion(self) -> bool:
        return bool(self.figura_proteccion)

    @property
    def es_bic(self) -> bool:
       return self.figura_proteccion.nivel == "BIC"
        
    @property
    def esta_geocodificado(self) -> bool:
        return self.latitud is not None and self.longitud is not None

    @property
    def vendido(self) -> bool:
        return bool(self.transmisiones)

    @property
    def esta_inmatriculado(self) -> bool:
        return self.inmatriculacion is not None

    @property
    def es_bic(self) -> bool:
        return self.grado_proteccion is not None and self.grado_proteccion.codigo == "BIC"

    @property
    def es_ruina(self) -> bool:
        return self.estado_conservacion is not None and self.estado_conservacion.codigo == "RUINA"


# ---------------------------------------------------------------------------
# Tablas satélite
# ---------------------------------------------------------------------------

class InmuebleDenominaciones(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_denominaciones"

    inmueble_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inmuebles.id"), index=True
    )
    denominacion: Mapped[str] = mapped_column(String(500), index=True)
    es_principal: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    idioma: Mapped[Optional[IdiomaInmueble]] = mapped_column(Enum(IdiomaInmueble), index=True)
    fecha_inicio: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(DateTime)

    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="denominaciones")

    @property
    def esta_vigente(self) -> bool:
        now = datetime.now()
        if self.fecha_inicio and now < self.fecha_inicio:
            return False
        if self.fecha_fin and now > self.fecha_fin:
            return False
        return True


class InmuebleOSMExt(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_osm_ext"

    inmueble_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inmuebles.id"), unique=True, index=True
    )
    osm_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    osm_type: Mapped[Optional[str]] = mapped_column(String(10))
    version: Mapped[Optional[int]] = mapped_column()
    name: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    denomination: Mapped[Optional[str]] = mapped_column(String(255))
    diocese: Mapped[Optional[str]] = mapped_column(String(255))
    operator: Mapped[Optional[str]] = mapped_column(String(255))
    heritage_status: Mapped[Optional[str]] = mapped_column(String(100))
    historic: Mapped[Optional[str]] = mapped_column(String(100))
    ruins: Mapped[bool] = mapped_column(Boolean, default=False)
    has_polygon: Mapped[bool] = mapped_column(Boolean, default=False)
    geom: Mapped[Optional[Geometry]] = mapped_column(Geometry("POINT", srid=4326))
    address_street: Mapped[Optional[str]] = mapped_column(String(255))
    address_city: Mapped[Optional[str]] = mapped_column(String(100))
    address_postcode: Mapped[Optional[str]] = mapped_column(String(10))
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    tags: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)
    qa_flags: Mapped[Optional[dict]] = mapped_column(JSONB)
    source_refs: Mapped[Optional[dict]] = mapped_column(JSONB)

    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="osm_ext", uselist=False)


class InmuebleWDExt(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_wd_ext"

    inmueble_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inmuebles.id"), unique=True, index=True
    )
    wikidata_qid: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    commons_category: Mapped[Optional[str]] = mapped_column(String(255))
    inception: Mapped[Optional[str]] = mapped_column(String(100))
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    claims: Mapped[Optional[dict]] = mapped_column(JSONB)
    sitelinks: Mapped[Optional[dict]] = mapped_column(JSONB)
    raw: Mapped[Optional[dict]] = mapped_column(JSONB)

    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="wd_ext", uselist=False)


class InmuebleInmatriculacion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_inmatriculacion"

    # --- claves foráneas ----------------------------------------------------
    inmueble_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("inmuebles.id"), unique=True, index=True
    )
    registro_propiedad_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("registros_propiedad.id"), index=True
    )
    documento_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documentos.id"), index=True
    )

    # --- datos propios de la nota simple / certificación -----------------
    ref_catastral: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    superficie_registral_m2: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    naturaleza_registral: Mapped[Optional[str]] = mapped_column(String(100))
    fecha_inscripcion: Mapped[Optional[Date]] = mapped_column(Date)

    # --- relaciones --------------------------------------------------------
    inmueble: Mapped["Inmueble"] = relationship(
        "Inmueble", back_populates="inmatriculacion", single_parent=True
    )
    registro_propiedad: Mapped[Optional["RegistroPropiedad"]] = relationship(
        "RegistroPropiedad", back_populates="inmatriculaciones"
    )
    documento: Mapped["Documento"] = relationship("Documento")