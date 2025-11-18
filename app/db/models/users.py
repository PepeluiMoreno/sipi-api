# models/users.py
from datetime import datetime, timezone  # ✅ CORREGIDO
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.mixins import UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoMixin
else:
    # ✅ Import en runtime para evitar problemas
    from app.db.mixins import UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoMixin

# Tabla de asociación muchos-a-muchos
usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", String(36), ForeignKey("usuarios.id"), primary_key=True),
    Column("rol_id", String(36), ForeignKey("roles.id"), primary_key=True),
    Column("fecha_asignacion", DateTime, default=lambda: datetime.now(timezone.utc)),  # ✅ CORREGIDO
    Column("asignado_por", String(36), ForeignKey("usuarios.id"), nullable=True),
)

class Usuario(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoMixin, Base):
    __tablename__ = "usuarios"
    
    nombre_usuario: Mapped[str] = mapped_column(String(100))
    hashed_contrasena: Mapped[str] = mapped_column(Text)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # ✅ FIX: Relaciones con joins explícitos
    roles: Mapped[list["Rol"]] = relationship(
        "Rol", 
        secondary=usuario_rol, 
        back_populates="usuarios",
        primaryjoin="Usuario.id == usuario_rol.c.usuario_id",
        secondaryjoin="usuario_rol.c.rol_id == Rol.id",
    )

class Rol(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "roles"
    
    nombre: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
     
    # ✅ FIX: Relaciones con joins explícitos
    usuarios: Mapped[list["Usuario"]] = relationship(
        "Usuario", 
        secondary=usuario_rol, 
        back_populates="roles",
        primaryjoin="Rol.id == usuario_rol.c.rol_id",
        secondaryjoin="usuario_rol.c.usuario_id == Usuario.id",
    )