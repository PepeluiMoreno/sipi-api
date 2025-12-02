# app/db/mixins/contacto.py
from typing import Optional
from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .direccion import DireccionMixin

class ContactoMixin:
    email_personal: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    email_corporativo: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    telefono: Mapped[Optional[str]] = mapped_column(String(20))
    telefono_movil: Mapped[Optional[str]] = mapped_column(String(20))
    fax: Mapped[Optional[str]] = mapped_column(String(20))
    sitio_web: Mapped[Optional[str]] = mapped_column(String(500))
    notas: Mapped[Optional[str]] = mapped_column(String(500))

class ContactoDireccionMixin(ContactoMixin, DireccionMixin):
    pass