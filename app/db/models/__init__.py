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
