# app/db/mixins/base.py
from datetime import datetime
# app/db/mixins/base.py
from datetime import datetime, timezone
import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr
from sqlalchemy.schema import ForeignKey

# ✅ CORRECCIÓN: Importar Usuario solo para type hints
if TYPE_CHECKING:
    from app.db.models.users import Usuario

class UUIDPKMixin:
    """Clave primaria UUID estándar"""
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

class AuditMixin:
    """Auditoría de creación, modificación y eliminación lógica"""
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=lambda: datetime.now(timezone.utc), index=True)
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
    
    # Relaciones (usando string references para evitar imports circulares)
    @declared_attr
    def created_by(cls) -> Mapped[Optional["Usuario"]]:
        return relationship("Usuario", foreign_keys=[cls.created_by_id], viewonly=True)
    
    @declared_attr
    def updated_by(cls) -> Mapped[Optional["Usuario"]]:
        return relationship("Usuario", foreign_keys=[cls.updated_by_id], viewonly=True)
    
    @declared_attr
    def deleted_by(cls) -> Mapped[Optional["Usuario"]]:
        return relationship("Usuario", foreign_keys=[cls.deleted_by_id], viewonly=True)
    
    # IPs de origen
    created_from_ip: Mapped[Optional[str]] = mapped_column(String(45))  # IPv6 = 45 chars
    updated_from_ip: Mapped[Optional[str]] = mapped_column(String(45))
    
    @property
    def esta_eliminado(self) -> bool:
        return self.deleted_at is not None
    
    def soft_delete(self, user_id: Optional[str] = None) -> None:
        """Marcar como eliminado (soft delete)"""
        self.deleted_at = datetime.now(timezone.utc)
        if user_id:
            self.deleted_by_id = user_id
    
    def restore(self) -> None:
        """Restaurar registro eliminado"""
        self.deleted_at = None
        self.deleted_by_id = None