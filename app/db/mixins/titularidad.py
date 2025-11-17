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
