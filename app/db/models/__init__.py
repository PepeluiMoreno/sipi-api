# models/__init__.py
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

# actores
from .actores import (
    Adquiriente, Administracion, AdministracionTitular, AgenciaInmobiliaria,
    ColegioProfesional, Diocesis, DiocesisTitular, Notaria,
    Tecnico, RegistroPropiedad, RegistroPropiedadTitular, Transmitente
)

# Catálogos
from .tipologias import (
    TipoEstadoConservacion, TipoEstadoTratamiento, TipoFiguraProteccion, TipoRolTecnico,
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


# Subvenciones
from .subvenciones import ActuacionSubvencion, SubvencionAdministracion

# Usuarios
from .users import Usuario, Rol, usuario_rol

__all__ = [
    'Base', 'UUIDPKMixin', 'AuditMixin',
    # actores
    'Adquiriente', 'Administracion', 'AdministracionTitular', 'AgenciaInmobiliaria',
    'ColegioProfesional', 'Diocesis', 'DiocesisTitular', 'Notaria', 
    'Tecnico', 'RegistroPropiedad', 'RegistroPropiedadTitular', 'Transmitente',
    # Catálogos
    'TipoEstadoConservacion', 'TipoEstadoTratamiento', 'TipoFiguraProteccion', 'TipoRolTecnico',
    'TipoCertificacionPropiedad', 'TipoDocumento', 'TipoInmueble', 'TipoMimeDocumento',
    'TipoPersona', 'TipoTransmision', 'TipoVia',
    # Geografía
    'ComunidadAutonoma', 'Provincia', 'Localidad',
    # Documentos
    'Documento', 'InmuebleDocumento', 'ActuacionDocumento', 'TransmisionDocumento',
    # Actuaciones
    'Actuacion', 'ActuacionTecnico',
    # Transmisiones
    'Transmision', 'Inmatriculacion', 'TransmisionAnunciante', 'Adquiriente', 'Transmitente',
    # Inmuebles
    'Inmueble', 'InmuebleOSMExt', 'InmuebleWDExt',
    # Historiografía
    'FuenteHistoriografica', 'CitaHistoriografica',
    # Protección
    'InmuebleTipoFiguraProteccion',
    # Subvenciones
    'ActuacionSubvencion', 'SubvencionAdministracion',
    # Usuarios
    'Usuario', 'Rol', 'usuario_rol'
]
