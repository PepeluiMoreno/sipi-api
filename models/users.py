# models/users.py
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship

# ✅ CORRECCIÓN: Base debe importarse normalmente para usar Base.metadata
from app.db.base import Base

if TYPE_CHECKING:
    from app.db.mixins import UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoMixin
else:
    # ✅ Import en runtime para evitar problemas
    from app.db.mixins import UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoMixin

# Tabla de asociación muchos-a-muchos (DEBE estar antes de las clases que la usan)
usuario_rol = Table(
    "usuario_rol",
    Base.metadata,
    Column("usuario_id", String(36), ForeignKey("usuarios.id"), primary_key=True),
    Column("rol_id", String(36), ForeignKey("roles.id"), primary_key=True),
    Column("fecha_asignacion", DateTime, default=lambda: datetime.now(datetime.timezone.utc)),
    Column("asignado_por", String(36), ForeignKey("usuarios.id"), nullable=True),
)

class Usuario(UUIDPKMixin, AuditMixin, IdentificacionMixin, ContactoMixin, Base):
    __tablename__ = "usuarios"
    
    nombre_usuario: Mapped[str] = mapped_column(String(100))
    hashed_contrasena: Mapped[str] = mapped_column(Text)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Relación con roles
    roles: Mapped[list["Rol"]] = relationship("Rol", secondary=usuario_rol, back_populates="usuarios")
    


class Rol(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "roles"
    
    nombre: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text)
     
    # Relación con usuarios
    usuarios: Mapped[list["Usuario"]] = relationship("Usuario", secondary=usuario_rol, back_populates="roles")