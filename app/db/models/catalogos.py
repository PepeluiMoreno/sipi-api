# models/catalogos.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, Integer, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .documentos import Documento
    from .agentes import Tecnico
    from .transmisiones import Transmision, Inmatriculacion
    from .inmuebles import Inmueble

class CatalogoBase(UUIDPKMixin, AuditMixin, Base):
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
    documentos: Mapped[list["Documento"]] = relationship("Documento", back_populates="tipo_documento")

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
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="tipo_transmision")

class TipoVia(CatalogoBase):
    __tablename__ = "tipos_via"


class TipoLicencia(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "tipos_licencia"
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    nombre_corto: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_licencia: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url_legal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    requiere_atribucion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permite_uso_comercial: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    permite_derivadas: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requiere_compartir_igual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    es_libre: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    es_open_source: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    es_copyleft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    jurisdiccion: Mapped[str | None] = mapped_column(String(50), nullable=True)
    familia: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    icono_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    popularidad: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recomendada: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    obsoleta: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    documentos: Mapped[list["Documento"]] = relationship("Documento", back_populates="tipo_licencia")
    
    @property
    def badge_text(self) -> str:
        return self.nombre_corto or self.codigo
    
    @property
    def es_creative_commons(self) -> bool:
        return self.familia == "Creative Commons"


class FuenteDocumental(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "fuentes_documentales"
    codigo: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    url_fuente: Mapped[str | None] = mapped_column(String(500), nullable=True)
    es_externa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    requiere_url_externa: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    permite_metadata_extra: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    licencia_predeterminada_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tipos_licencia.id"), nullable=True)
    categoria: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    soporta_sincronizacion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    frecuencia_sync_dias: Mapped[int | None] = mapped_column(Integer, nullable=True)
    api_endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    requiere_autenticacion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    icono: Mapped[str | None] = mapped_column(String(100), nullable=True)
    color_hex: Mapped[str | None] = mapped_column(String(7), nullable=True)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    licencia_predeterminada: Mapped["TipoLicencia"] = relationship("TipoLicencia", foreign_keys=[licencia_predeterminada_id])
    documentos: Mapped[list["Documento"]] = relationship("Documento", back_populates="fuente_documental")
    
    @property
    def badge_text(self) -> str:
        return self.nombre
    
    @property
    def necesita_storage_propio(self) -> bool:
        return not self.requiere_url_externa