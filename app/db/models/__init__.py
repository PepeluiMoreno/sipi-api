# models/__init__.py
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

# Actores
from .actores import (
    Adquiriente, Administracion, AdministracionTitular, AgenciaInmobiliaria,
    ColegioProfesional, Diocesis, DiocesisTitular, Notaria,
    Tecnico, RegistroPropiedad, RegistroPropiedadTitular, Transmitente
)

# Tipologías
from .tipologias import (
    TipoEstadoConservacion, TipoEstadoTratamiento, TipoRolTecnico,
    TipoCertificacionPropiedad, TipoDocumento, TipoInmueble, TipoMimeDocumento,
    TipoPersona, TipoTransmision, TipoVia, TipoLicencia, FuenteDocumental
)

# Geografía
from .geografia import ComunidadAutonoma, Provincia, Municipio

# Documentos
from .documentos import Documento, InmuebleDocumento, ActuacionDocumento, TransmisionDocumento

# Actuaciones
from .actuaciones import Actuacion, ActuacionTecnico

# Transmisiones
from .transmisiones import Transmision, TransmisionAnunciante

# Inmuebles (incluye InmuebleCita)
from .inmuebles import (
    Inmueble, Inmatriculacion, InmuebleDenominacion, 
    InmuebleOSMExt, InmuebleWDExt, InmuebleCita
)

# Historiografía
from .historiografia import FuenteHistoriografica

# Figuras de Protección
from .figuras_proteccion import FiguraProteccion, NivelProteccion

# Subvenciones
from .subvenciones import ActuacionSubvencion, SubvencionAdministracion

# Usuarios
from .users import Usuario, Rol

__all__ = [
    'Base', 'UUIDPKMixin', 'AuditMixin',
    # Actores
    'Adquiriente', 'Administracion', 'AdministracionTitular', 'AgenciaInmobiliaria',
    'ColegioProfesional', 'Diocesis', 'DiocesisTitular', 'Notaria',
    'Tecnico', 'RegistroPropiedad', 'RegistroPropiedadTitular', 'Transmitente',
    # Tipologías
    'TipoEstadoConservacion', 'TipoEstadoTratamiento', 'TipoRolTecnico',
    'TipoCertificacionPropiedad', 'TipoDocumento', 'TipoInmueble', 'TipoMimeDocumento',
    'TipoPersona', 'TipoTransmision', 'TipoVia', 'TipoLicencia', 'FuenteDocumental',
    # Geografía
    'ComunidadAutonoma', 'Provincia', 'Municipio',
    # Documentos
    'Documento', 'InmuebleDocumento', 'ActuacionDocumento', 'TransmisionDocumento',
    # Actuaciones
    'Actuacion', 'ActuacionTecnico',
    # Transmisiones
    'Transmision', 'TransmisionAnunciante',
    # Inmuebles
    'Inmueble', 'Inmatriculacion', 'InmuebleDenominacion',
    'InmuebleOSMExt', 'InmuebleWDExt', 'InmuebleCita',
    # Historiografía
    'FuenteHistoriografica',
    # Figuras de Protección
    'FiguraProteccion', 'NivelProteccion',
    # Subvenciones
    'ActuacionSubvencion', 'SubvencionAdministracion',
    # Usuarios
    'Usuario', 'Rol'
]