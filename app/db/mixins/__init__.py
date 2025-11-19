# app/db/mixins/__init__.py
from .base import UUIDPKMixin, AuditMixin
from .identificacion import TipoIdentificacion, IdentificacionMixin
from .contacto import ContactoMixin, ContactoDireccionMixin
from .direccion import DireccionMixin
from .titularidad import TitularidadMixin
from .documento import DocumentoMixin

__all__ = [
    "UUIDPKMixin",
    "AuditMixin",
    "TipoIdentificacion",
    "IdentificacionMixin",
    "ContactoMixin",
    "ContactoDireccionMixin",
    "DireccionMixin",
    "TitularidadMixin",
    "DocumentoMixin",
]
