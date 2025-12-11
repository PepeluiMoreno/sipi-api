from __future__ import annotations
from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Boolean

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

class FuenteHistoriografica(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "fuentes_historiograficas"

    nombre: Mapped[str] = mapped_column(String(255), index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Relacion con InmuebleCita (definida en inmuebles.py)
    citas_bibliograficas: Mapped[List["InmuebleCita"]] = relationship(
        "InmuebleCita", back_populates="fuente", cascade="all, delete-orphan"
    )