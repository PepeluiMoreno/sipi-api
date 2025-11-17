#!/bin/bash
set -e

# ============================================================
# SCRIPT DE GENERACIÓN COMPLETA DE MIXINS Y MODELOS
# Ejecutar desde la raíz del proyecto
# ============================================================

echo "🚀 Iniciando generación de estructura completa..."

# Crear directorios
mkdir -p app/db/mixins
mkdir -p models

# ============================================================
# ARCHIVO BASE (proporcionado por el usuario)
# ============================================================
cat > app/db/base.py << 'EOF'
# /db/base.py
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase):
    __table_args__ = {'extend_existing': True}
    pass
EOF

# ============================================================
# MIXINS
# ============================================================

# app/db/mixins/__init__.py
cat > app/db/mixins/__init__.py << 'EOF'
# app/db/mixins/__init__.py
from .base import UUIDPKMixin, AuditMixin
from .identificacion import TipoIdentificacion, IdentificacionMixin
from .contacto import ContactoMixin, ContactoDireccionMixin
from .direccion import DireccionMixin
from .titularidad import TitularidadMixin

__all__ = [
    "UUIDPKMixin",
    "AuditMixin",
    "TipoIdentificacion",
    "IdentificacionMixin",
    "ContactoMixin",
    "ContactoDireccionMixin",
    "DireccionMixin",
    "TitularidadMixin"
]
EOF

# app/db/mixins/base.py
cat > app/db/mixins/base.py << 'EOF'
# app/db/mixins/base.py
from datetime import datetime
import uuid
from typing import Optional
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr

class UUIDPKMixin:
    """Clave primaria UUID estándar"""
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

class AuditMixin:
    """Auditoría de creación, modificación y eliminación lógica"""
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)  # Soft delete
    
    # Usuarios responsables (relaciones diferidas)
    @declared_attr
    def created_by_id(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(36), ForeignKey("usuarios.id"), index=True)
    
    @declared_attr
    def updated_by_id(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(36), ForeignKey("usuarios.id"), index=True)
    
    @declared_attr
    def deleted_by_id(cls) -> Mapped[Optional[str]]:
        return mapped_column(String(36), ForeignKey("usuarios.id"), index=True)
    
    # Relaciones
    @declared_attr
    def created_by(cls) -> Mapped[Optional["Usuario"]]:
        return relationship("Usuario", foreign_keys=[cls.created_by_id], back_populates="_created_records")
    
    @declared_attr
    def updated_by(cls) -> Mapped[Optional["Usuario"]]:
        return relationship("Usuario", foreign_keys=[cls.updated_by_id], back_populates="_updated_records")
    
    @declared_attr
    def deleted_by(cls) -> Mapped[Optional["Usuario"]]:
        return relationship("Usuario", foreign_keys=[cls.deleted_by_id], back_populates="_deleted_records")
    
    # IPs de origen
    created_from_ip: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 = 45 chars
    updated_from_ip: Mapped[Optional[str]] = mapped_column(String(45))
    
    @property
    def esta_eliminado(self) -> bool:
        return self.deleted_at is not None
    
    def soft_delete(self, user_id: Optional[str] = None) -> None:
        """Marcar como eliminado (soft delete)"""
        self.deleted_at = datetime.utcnow()
        if user_id:
            self.deleted_by_id = user_id
    
    def restore(self) -> None:
        """Restaurar registro eliminado"""
        self.deleted_at = None
        self.deleted_by_id = None
EOF

# app/db/mixins/identificacion.py
cat > app/db/mixins/identificacion.py << 'EOF'
# app/db/mixins/identificacion.py
import enum
from typing import Optional
from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column

class TipoIdentificacion(str, enum.Enum):
    """Tipos de documento de identidad"""
    DNI = "dni"
    NIE = "nie"
    NIF = "nif"
    CIF = "cif"
    PASAPORTE = "pasaporte"
    CIF_EXTRANJERO = "cif_extranjero"
    OTRO = "otro"

class IdentificacionMixin:
    """Mixin unificado para identificación de personas (físicas y jurídicas)"""
    
    tipo_identificacion: Mapped[Optional[TipoIdentificacion]] = mapped_column(Enum(TipoIdentificacion), index=True)
    identificacion: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    nombre: Mapped[str] = mapped_column(String(255))  # Campo unificado
    
    # Campos específicos para persona física
    apellidos: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Campo específico para persona jurídica
    identificacion_extranjera: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    @property
    def nombre_completo(self) -> str:
        """Nombre completo formateado según tipo de persona"""
        if self.apellidos:
            return f"{self.nombre} {self.apellidos}"
        return self.nombre
EOF

# app/db/mixins/direccion.py
cat > app/db/mixins/direccion.py << 'EOF'
# app/db/mixins/direccion.py
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr

if TYPE_CHECKING:
    from app.models.geografia import Provincia, Localidad, ComunidadAutonoma
    from app.models.catalogos import TipoVia

class DireccionMixin:
    """Mixin para datos de dirección geográfica"""
    
    # Componentes de dirección
    tipo_via_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_via.id"), index=True)
    nombre_via: Mapped[Optional[str]] = mapped_column(String(255))
    numero: Mapped[Optional[str]] = mapped_column(String(10))
    bloque: Mapped[Optional[str]] = mapped_column(String(10))
    escalera: Mapped[Optional[str]] = mapped_column(String(10))
    piso: Mapped[Optional[str]] = mapped_column(String(10))
    puerta: Mapped[Optional[str]] = mapped_column(String(10))
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    
    # Referencias geográficas
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True)
    provincia_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    localidad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("localidades.id"), index=True)
    
    # Coordenadas
    latitud: Mapped[Optional[Decimal]] = mapped_column(Float(precision=10, asdecimal=True), nullable=True)
    longitud: Mapped[Optional[Decimal]] = mapped_column(Float(precision=10, asdecimal=True), nullable=True)
    
    # Relaciones (declaradas correctamente)
    @declared_attr
    def tipo_via(cls) -> Mapped[Optional["TipoVia"]]:
        return relationship("TipoVia", lazy="joined")
    
    @declared_attr
    def comunidad_autonoma(cls) -> Mapped[Optional["ComunidadAutonoma"]]:
        return relationship("ComunidadAutonoma", lazy="joined")
    
    @declared_attr
    def provincia(cls) -> Mapped[Optional["Provincia"]]:
        return relationship("Provincia", lazy="joined")
    
    @declared_attr
    def localidad(cls) -> Mapped[Optional["Localidad"]]:
        return relationship("Localidad", lazy="joined")
    
    @property
    def direccion_completa(self) -> str:
        """Dirección completa formateada"""
        partes = []
        
        if self.tipo_via and self.nombre_via:
            partes.append(f"{self.tipo_via.nombre} {self.nombre_via}")
        elif self.nombre_via:
            partes.append(self.nombre_via)
        
        if self.numero:
            partes.append(f", nº {self.numero}")
        
        detalles = []
        for label, valor in [
            ("Bloque", self.bloque),
            ("Esc.", self.escalera),
            ("Piso", self.piso),
            ("Puerta", self.puerta)
        ]:
            if valor:
                detalles.append(f"{label} {valor}")
        
        if detalles:
            partes.append(f" ({', '.join(detalles)})")
        
        if self.codigo_postal and self.localidad:
            partes.append(f" - {self.codigo_postal} {self.localidad.nombre}")
        elif self.codigo_postal:
            partes.append(f" - {self.codigo_postal}")
        elif self.localidad:
            partes.append(f" - {self.localidad.nombre}")
        
        return "".join(partes).strip()
    
    @property
    def direccion_corta(self) -> str:
        """Dirección corta: tipo vía + nombre + número"""
        partes = []
        if self.tipo_via and self.nombre_via:
            partes.append(f"{self.tipo_via.nombre} {self.nombre_via}")
        elif self.nombre_via:
            partes.append(self.nombre_via)
        if self.numero:
            partes.append(f", {self.numero}")
        return "".join(partes).strip()
EOF

# app/db/mixins/contacto.py
cat > app/db/mixins/contacto.py << 'EOF'
# app/db/mixins/contacto.py
from typing import Optional
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .direccion import DireccionMixin

class ContactoMixin:
    """Datos de contacto estándar"""
    
    email: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    telefono_movil: Mapped[Optional[str]] = mapped_column(String(20))
    fax: Mapped[Optional[str]] = mapped_column(String(20))
    sitio_web: Mapped[Optional[str]] = mapped_column(String(500))
    notas: Mapped[Optional[str]] = mapped_column(String(500))

class ContactoDireccionMixin(ContactoMixin, DireccionMixin):
    """Mixin combinado: contacto + dirección"""
    pass
EOF

# app/db/mixins/titularidad.py
cat > app/db/mixins/titularidad.py << 'EOF'
# app/db/mixins/titularidad.py
from typing import TypeVar, Generic, List, Optional
from sqlalchemy.orm import Mapped, relationship, declared_attr
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

T = TypeVar('T')

class TitularidadMixin(Generic[T]):
    """
    Mixin para entidades con titulares temporales (obispos, notarios, etc.)
    
    USO EN MODELO PRINCIPAL:
    class Notaria(Base, TitularidadMixin["NotariaTitular"]):
        DENOMINACION_TITULARIDAD = "notario"
        # ... campos ...
        
    USO EN MODELO TITULAR:
    class NotariaTitular(UUIDPKMixin, AuditMixin, Base):
        notaria_id: Mapped[str] = ForeignKey("notarias.id")
        fecha_inicio: Mapped[datetime]
        fecha_fin: Mapped[Optional[datetime]]
    """
    
    DENOMINACION_TITULARIDAD: str = None  # "notario", "registrador", etc.
    
    @declared_attr
    def titulares(cls) -> Mapped[List[T]]:
        """Relación con todos los titulares"""
        return relationship(
            f"{cls.__name__}Titular",
            back_populates=cls.DENOMINACION_TITULARIDAD,
            cascade="all, delete-orphan",
            lazy="selectin"
        )
    
    @property
    def titular_actual(self) -> Optional[T]:
        """Titular actual (sin fecha_fin)"""
        if not hasattr(self, "_titular_actual_cache"):
            self._titular_actual_cache = next(
                (t for t in self.titulares if getattr(t, "fecha_fin", None) is None),
                None
            )
        return self._titular_actual_cache
    
    @property
    def tiene_titular(self) -> bool:
        """¿Hay titular actualmente asignado?"""
        return self.titular_actual is not None
    
    @property
    def titulares_anteriores(self) -> List[T]:
        """Lista de titulares históricos (con fecha_fin)"""
        return [t for t in self.titulares if getattr(t, "fecha_fin", None) is not None]
EOF

# ============================================================
# MODELOS
# ============================================================

# models/__init__.py
cat > models/__init__.py << 'EOF'
# models/__init__.py
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

# Agentes
from .agentes import (
    Adquiriente, Administracion, AdministracionTitular, AgenciaInmobiliaria,
    ColegioProfesional, Diocesis, DiocesisTitular, Notaria, NotariaTitular,
    Tecnico, RegistroPropiedad, RegistroTitular, Transmitente
)

# Catálogos
from .catalogos import (
    EstadoConservacion, EstadoTratamiento, FiguraProteccion, RolTecnico,
    TipoCertificacionPropiedad, TipoDocumento, TipoInmueble, TipoMimeDocumento,
    TipoPersona, TipoTransmision, TipoVia
)

# Geografía
from .geografia import ComunidadAutonoma, Provincia, Localidad

# Documentos
from .documentos import Documento, InmuebleDocumento, ActuacionDocumento, TransmisionDocumento

# Actuaciones
from .actuaciones import Actuacion, ActuacionTecnico

# Transmisiones
from .transmisiones import Transmision, Inmatriculacion, TransmisionAnunciante

# Inmuebles
from .inmuebles import Inmueble, InmuebleOSMExt, InmuebleWDExt

# Historiografía
from .historiografia import FuenteHistoriografica, CitaHistoriografica

# Protección
from .proteccion import InmuebleFiguraProteccion

# Subvenciones
from .subvenciones import ActuacionSubvencion, SubvencionAdministracion

# Usuarios
from .users import Usuario, Rol, usuario_rol

__all__ = [
    'Base', 'UUIDPKMixin', 'AuditMixin',
    # Agentes
    'Adquiriente', 'Administracion', 'AdministracionTitular', 'AgenciaInmobiliaria',
    'ColegioProfesional', 'Diocesis', 'DiocesisTitular', 'Notaria', 'NotariaTitular',
    'Tecnico', 'RegistroPropiedad', 'RegistroTitular', 'Transmitente',
    # Catálogos
    'EstadoConservacion', 'EstadoTratamiento', 'FiguraProteccion', 'RolTecnico',
    'TipoCertificacionPropiedad', 'TipoDocumento', 'TipoInmueble', 'TipoMimeDocumento',
    'TipoPersona', 'TipoTransmision', 'TipoVia',
    # Geografía
    'ComunidadAutonoma', 'Provincia', 'Localidad',
    # Documentos
    'Documento', 'InmuebleDocumento', 'ActuacionDocumento', 'TransmisionDocumento',
    # Actuaciones
    'Actuacion', 'ActuacionTecnico',
    # Transmisiones
    'Transmision', 'Inmatriculacion', 'TransmisionAnunciante',
    # Inmuebles
    'Inmueble', 'InmuebleOSMExt', 'InmuebleWDExt',
    # Historiografía
    'FuenteHistoriografica', 'CitaHistoriografica',
    # Protección
    'InmuebleFiguraProteccion',
    # Subvenciones
    'ActuacionSubvencion', 'SubvencionAdministracion',
    # Usuarios
    'Usuario', 'Rol', 'usuario_rol'
]
EOF

# models/catalogos.py
cat > models/catalogos.py << 'EOF'
# models/catalogos.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .agentes import Tecnico
    from .transmisiones import Transmision, Inmatriculacion
    from .inmuebles import Inmueble

class CatalogoBase(UUIDPKMixin, AuditMixin, Base):
    """Base para catálogos simples (nombre + descripción)"""
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

class TipoVia(CatalogoBase):
    __tablename__ = "tipos_via"
EOF

# models/geografia.py
cat > models/geografia.py << 'EOF'
# models/geografia.py
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .agentes import Notaria, RegistroPropiedad, Administracion
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

class Localidad(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "localidades"
    
    nombre: Mapped[str] = mapped_column(String(100), index=True)
    provincia_id: Mapped[str] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    
    # Relaciones
    provincia: Mapped["Provincia"] = relationship("Provincia", back_populates="localidades")
    notarias: Mapped[list["Notaria"]] = relationship("Notaria", back_populates="localidad")
    registros_propiedad: Mapped[list["RegistroPropiedad"]] = relationship("RegistroPropiedad", back_populates="localidad")
    agencias_inmobiliarias: Mapped[list["AgenciaInmobiliaria"]] = relationship("AgenciaInmobiliaria", back_populates="localidad")
EOF

# models/documentos.py
cat > models/documentos.py << 'EOF'
# models/documentos.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .actuaciones import Actuacion
    from .transmisiones import Transmision
    from .catalogos import TipoDocumento

class Documento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "documentos"
    
    url: Mapped[str] = mapped_column(Text)
    nombre_archivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tamano_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hash_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

class InmuebleDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_documentos"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id"), index=True)
    tipo_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("tipos_documento.id"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_documento: Mapped[DateTime | None] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="documentos")
    tipo_documento: Mapped["TipoDocumento"] = relationship("TipoDocumento", back_populates="inmuebles_documentos")

class ActuacionDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "actuaciones_documentos"
    
    actuacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones.id"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id"), index=True)
    tipo_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("tipos_documento.id"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    actuacion: Mapped["Actuacion"] = relationship("Actuacion", back_populates="documentos")
    tipo_documento: Mapped["TipoDocumento"] = relationship("TipoDocumento", back_populates="actuaciones_documentos")

class TransmisionDocumento(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "transmisiones_documentos"
    
    transmision_id: Mapped[str] = mapped_column(String(36), ForeignKey("transmisiones.id"), index=True)
    documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("documentos.id"), index=True)
    tipo_documento_id: Mapped[str] = mapped_column(String(36), ForeignKey("tipos_documento.id"), index=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    transmision: Mapped["Transmision"] = relationship("Transmision", back_populates="documentos")
    tipo_documento: Mapped["TipoDocumento"] = relationship("TipoDocumento", back_populates="transmisiones_documentos")
EOF

# models/actuaciones.py
cat > models/actuaciones.py << 'EOF'
# models/actuaciones.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, Numeric
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .agentes import Tecnico
    from .catalogos import RolTecnico
    from .documentos import ActuacionDocumento
    from .subvenciones import ActuacionSubvencion

class Actuacion(UUIDPKMixin, AuditMixin, Base):
    """Intervenciones/actuaciones realizadas sobre un inmueble"""
    __tablename__ = "actuaciones"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    
    # Fechas
    fecha_inicio: Mapped[Optional[datetime]] = mapped_column(index=True)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(index=True)
    
    # Presupuesto
    presupuesto: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="actuaciones")
    tecnicos: Mapped[list["ActuacionTecnico"]] = relationship("ActuacionTecnico", back_populates="actuacion", cascade="all, delete-orphan")
    documentos: Mapped[list["ActuacionDocumento"]] = relationship("ActuacionDocumento", back_populates="actuacion", cascade="all, delete-orphan")
    subvenciones: Mapped[list["ActuacionSubvencion"]] = relationship("ActuacionSubvencion", back_populates="actuacion", cascade="all, delete-orphan")

class ActuacionTecnico(UUIDPKMixin, AuditMixin, Base):
    """Técnicos asignados a una actuación con roles específicos"""
    __tablename__ = "actuaciones_tecnicos"
    
    actuacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones.id"), index=True)
    tecnico_id: Mapped[str] = mapped_column(String(36), ForeignKey("tecnicos.id"), index=True)
    rol_tecnico_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles_tecnico.id"), index=True)
    
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    fecha_inicio: Mapped[Optional[datetime]] = mapped_column(index=True)
    fecha_fin: Mapped[Optional[datetime]] = mapped_column(index=True)
    
    # Relaciones
    actuacion: Mapped["Actuacion"] = relationship("Actuacion", back_populates="tecnicos")
    tecnico: Mapped["Tecnico"] = relationship("Tecnico", back_populates="actuaciones")
    rol_tecnico: Mapped["RolTecnico"] = relationship("RolTecnico", lazy="joined")
EOF

# models/transmisiones.py
cat > models/transmisiones.py << 'EOF'
# models/transmisiones.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Numeric, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .agentes import Adquiriente, Transmitente, Notaria, RegistroPropiedad, AgenciaInmobiliaria
    from .catalogos import TipoTransmision, TipoCertificacionPropiedad
    from .documentos import TransmisionDocumento

class Transmision(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "transmisiones"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    transmitente_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transmitentes.id"), index=True)
    adquiriente_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("adquirientes.id"), index=True)
    notaria_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("notarias.id"), index=True)
    registro_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("registros_propiedad.id"), index=True)
    tipo_transmision_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_transmision.id"), index=True)
    tipo_certificacion_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_certificacion_propiedad.id"), index=True)
    
    fecha_transmision: Mapped[Optional[datetime]] = mapped_column(index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    precio_venta: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="transmisiones", foreign_keys=[inmueble_id])
    transmitente: Mapped[Optional["Transmitente"]] = relationship("Transmitente", back_populates="transmisiones")
    adquiriente: Mapped[Optional["Adquiriente"]] = relationship("Adquiriente", back_populates="transmisiones")
    notaria: Mapped[Optional["Notaria"]] = relationship("Notaria", back_populates="transmisiones")
    registro_propiedad: Mapped[Optional["RegistroPropiedad"]] = relationship("RegistroPropiedad", back_populates="transmisiones")
    tipo_transmision: Mapped[Optional["TipoTransmision"]] = relationship("TipoTransmision", back_populates="transmisiones")
    tipo_certificacion_propiedad: Mapped[Optional["TipoCertificacionPropiedad"]] = relationship("TipoCertificacionPropiedad", back_populates="transmisiones")
    documentos: Mapped[list["TransmisionDocumento"]] = relationship("TransmisionDocumento", back_populates="transmision", cascade="all, delete-orphan")
    anunciantes: Mapped[list["TransmisionAnunciante"]] = relationship("TransmisionAnunciante", back_populates="transmision", cascade="all, delete-orphan")

class Inmatriculacion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmatriculaciones"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), unique=True, nullable=False)
    registro_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("registros_propiedad.id"), index=True)
    tipo_certificacion_propiedad_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_certificacion_propiedad.id"), index=True)
    fecha: Mapped[Optional[datetime]] = mapped_column(index=True)
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="inmatriculacion", uselist=False)
    registro_propiedad: Mapped[Optional["RegistroPropiedad"]] = relationship("RegistroPropiedad", back_populates="inmatriculaciones")
    tipo_certificacion_propiedad: Mapped[Optional["TipoCertificacionPropiedad"]] = relationship("TipoCertificacionPropiedad", back_populates="inmatriculaciones")

class TransmisionAnunciante(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "transmision_anunciantes"
    
    transmision_id: Mapped[str] = mapped_column(String(36), ForeignKey("transmisiones.id"), index=True)
    agencia_inmobiliaria_id: Mapped[str] = mapped_column(String(36), ForeignKey("agencias_inmobiliarias.id"), index=True)
    
    # Relaciones
    transmision: Mapped["Transmision"] = relationship("Transmision", back_populates="anunciantes")
    agencia_inmobiliaria: Mapped["AgenciaInmobiliaria"] = relationship("AgenciaInmobiliaria", back_populates="transmisiones_anunciadas")
EOF

# models/inmuebles.py
cat > models/inmuebles.py << 'EOF'
# models/inmuebles.py
from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean, ForeignKey, Numeric, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from geoalchemy2 import Geometry
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .geografia import Localidad, Provincia, ComunidadAutonoma
    from .agentes import Diocesis
    from .catalogos import TipoInmueble, EstadoConservacion, EstadoTratamiento, TipoVia
    from .transmisiones import Transmision, Inmatriculacion
    from .actuaciones import Actuacion
    from .documentos import InmuebleDocumento
    from .historiografia import CitaHistoriografica
    from .proteccion import InmuebleFiguraProteccion

class Inmueble(UUIDPKMixin, AuditMixin, Base):
    """Modelo principal de inmuebles patrimoniales"""
    __tablename__ = "inmuebles"
    
    # Identificación
    nombre: Mapped[Optional[str]] = mapped_column(String(255), index=True)
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
    transmisiones: Mapped[list["Transmision"]] = relationship("Transmision", back_populates="inmueble", cascade="all, delete-orphan")
    actuaciones: Mapped[list["Actuacion"]] = relationship("Actuacion", back_populates="inmueble", cascade="all, delete-orphan")
    documentos: Mapped[list["InmuebleDocumento"]] = relationship("InmuebleDocumento", back_populates="inmueble", cascade="all, delete-orphan")
    citas_historiograficas: Mapped[list["CitaHistoriografica"]] = relationship("CitaHistoriografica", back_populates="inmueble", cascade="all, delete-orphan")
    figuras_proteccion: Mapped[list["InmuebleFiguraProteccion"]] = relationship("InmuebleFiguraProteccion", back_populates="inmueble", cascade="all, delete-orphan")
    
    # Relaciones 1:1
    inmatriculacion: Mapped[Optional["Inmatriculacion"]] = relationship("Inmatriculacion", back_populates="inmueble", uselist=False, cascade="all, delete-orphan")
    osm_ext: Mapped[Optional["InmuebleOSMExt"]] = relationship("InmuebleOSMExt", back_populates="inmueble", uselist=False, cascade="all, delete-orphan")
    wd_ext: Mapped[Optional["InmuebleWDExt"]] = relationship("InmuebleWDExt", back_populates="inmueble", uselist=False, cascade="all, delete-orphan")

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
EOF

# models/agentes.py
cat > models/agentes.py << 'EOF'
# models/agentes.py
from __future__ import annotations
from datetime import datetime
from typing import TYPE_CHECKING, Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey
from app.db.base import Base
from app.db.mixins import (
    UUIDPKMixin, AuditMixin, IdentificacionMixin, 
    ContactoDireccionMixin, TitularidadMixin
)

if TYPE_CHECKING:
    from .inmuebles import Inmueble
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
EOF

# models/historiografia.py
cat > models/historiografia.py << 'EOF'
# models/historiografia.py
from __future__ import annotations
from typing import TYPE_CHECKING
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble

class FuenteHistoriografica(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "fuentes_historiograficas"
    
    titulo: Mapped[str] = mapped_column(String(500), index=True)
    autor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    editorial: Mapped[str | None] = mapped_column(String(255), nullable=True)
    anno_publicacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    isbn: Mapped[str | None] = mapped_column(String(20), nullable=True)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    citas: Mapped[list["CitaHistoriografica"]] = relationship("CitaHistoriografica", back_populates="fuente", cascade="all, delete-orphan")

class CitaHistoriografica(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "citas_historiograficas"
    
    fuente_id: Mapped[str] = mapped_column(String(36), ForeignKey("fuentes_historiograficas.id"), index=True)
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    paginas: Mapped[str | None] = mapped_column(String(100), nullable=True)
    texto_cita: Mapped[str] = mapped_column(Text)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    fuente: Mapped["FuenteHistoriografica"] = relationship("FuenteHistoriografica", back_populates="citas")
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="citas_historiograficas")
EOF

# models/proteccion.py
cat > models/proteccion.py << 'EOF'
# models/proteccion.py
from __future__ import annotations
from typing import TYPE_CHECKING
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .inmuebles import Inmueble
    from .catalogos import FiguraProteccion
    from .agentes import Administracion

class InmuebleFiguraProteccion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "inmuebles_figuras_proteccion"
    
    inmueble_id: Mapped[str] = mapped_column(String(36), ForeignKey("inmuebles.id"), index=True)
    figura_proteccion_id: Mapped[str] = mapped_column(String(36), ForeignKey("figuras_proteccion.id"), index=True)
    administracion_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("administraciones.id"), index=True, nullable=True)
    bic_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    norma: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_declaracion: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # Relaciones
    inmueble: Mapped["Inmueble"] = relationship("Inmueble", back_populates="figuras_proteccion")
    figura_proteccion: Mapped["FiguraProteccion"] = relationship("FiguraProteccion")
    administracion: Mapped["Administracion"] = relationship("Administracion")
EOF

# models/subvenciones.py
cat > models/subvenciones.py << 'EOF'
# models/subvenciones.py
from __future__ import annotations
from typing import TYPE_CHECKING
from decimal import Decimal
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Numeric, ForeignKey
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

if TYPE_CHECKING:
    from .actuaciones import Actuacion
    from .agentes import Administracion

class ActuacionSubvencion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "actuaciones_subvenciones"
    
    actuacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones.id"), index=True)
    codigo_concesion: Mapped[str] = mapped_column(String(100), index=True)
    importe_aplicado: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    porcentaje_financiacion: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    justificacion_gasto: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Relaciones
    actuacion: Mapped["Actuacion"] = relationship("Actuacion", back_populates="subvenciones")
    administraciones: Mapped[list["SubvencionAdministracion"]] = relationship("SubvencionAdministracion", back_populates="subvencion", cascade="all, delete-orphan")

class SubvencionAdministracion(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "subvenciones_administraciones"
    
    subvencion_id: Mapped[str] = mapped_column(String(36), ForeignKey("actuaciones_subvenciones.id"), index=True)
    administracion_id: Mapped[str] = mapped_column(String(36), ForeignKey("administraciones.id"), index=True)
    importe_aportado: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    porcentaje_participacion: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    
    # Relaciones
    subvencion: Mapped["ActuacionSubvencion"] = relationship("ActuacionSubvencion", back_populates="administraciones")
    administracion: Mapped["Administracion"] = relationship("Administracion")
EOF

# models/users.py
cat > models/users.py << 'EOF'
# models/users.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

# Tabla de asociación muchos-a-muchos
usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", String(36), ForeignKey("usuarios.id"), primary_key=True),
    Column("rol_id", String(36), ForeignKey("roles.id"), primary_key=True),
    Column("fecha_asignacion", DateTime, default=datetime.utcnow),
    Column("asignado_por", String(36), ForeignKey("usuarios.id"), nullable=True),
)

class Usuario(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "usuarios"
    
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100))
    apellidos: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relaciones
    roles: Mapped[list["Rol"]] = relationship(
        "Rol",
        secondary=usuario_rol,
        back_populates="usuarios"
    )
    _created_records: Mapped[list["Base"]] = relationship("Base", foreign_keys="[Base.created_by_id]")
    _updated_records: Mapped[list["Base"]] = relationship("Base", foreign_keys="[Base.updated_by_id]")
    _deleted_records: Mapped[list["Base"]] = relationship("Base", foreign_keys="[Base.deleted_by_id]")

class Rol(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "roles"
    
    nombre: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Relaciones
    usuarios: Mapped[list["Usuario"]] = relationship(
        "Usuario",
        secondary=usuario_rol,
        back_populates="roles"
    )
EOF

# ============================================================
# VERIFICACIÓN
# ============================================================

echo "✅ Verificando archivos creados..."
echo ""

# Contar archivos
MIXIN_FILES=$(find app/db/mixins -name "*.py" | wc -l)
MODEL_FILES=$(find models -name "*.py" | wc -l)

echo "📊 Resumen:"
echo "   Mixins creados: $MIXIN_FILES"
echo "   Modelos creados: $MODEL_FILES"
echo ""

echo "📁 Estructura completa:"
tree app/db/mixins models 2>/dev/null || find app/db/mixins models -name "*.py" | sort

echo ""
echo "🎯 Próximos pasos recomendados:"
echo "   1. Revisa los archivos generados en app/db/mixins/ y models/"
echo "   2. Ajusta las rutas de importación en tu proyecto si es necesario"
echo "   3. Ejecuta: alembic revision --autogenerate -m 'refactor modelos mejorados'"
echo "   4. REVISA LA MIGRACIÓN ANTES DE APLICAR (cambios de String a DateTime/Numeric)"
echo "   5. Si todo es correcto: alembic upgrade head"
echo "   6. Ejecuta tus tests para verificar todo funciona"

# Fin
echo ""
echo "🚀 ¡Generación completada con éxito!"
