# app/db/mixins/titularidad.py
from typing import List, Optional
from sqlalchemy.orm import Mapped, relationship, declared_attr
import re

def camel_to_snake(name: str) -> str:
    """Convierte CamelCase a snake_case"""
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

class TitularidadMixin:
    """
    Mixin para entidades con titulares temporales
    
    USO EN MODELO PRINCIPAL:
    class Notaria(Base, TitularidadMixin):
        # ... campos ...
        
    USO EN MODELO TITULAR:
    class NotariaTitular(TitularBase):
        notaria_id: Mapped[str] = ForeignKey("notarias.id")
        notaria: Mapped["Notaria"] = relationship("Notaria", back_populates="titulares")
    
    ACCESO:
    - notaria.titulares → Lista completa histórica
    - notaria.titular_actual → El titular actual (sin fecha_fin)
    - notaria.tiene_titular → bool
    - notaria.titulares_anteriores → Los históricos
    """
    
    @declared_attr
    def titulares(cls):
        """Relación con todos los titulares (histórico completo)"""
        return relationship(
            f"{cls.__name__}Titular",
            back_populates=camel_to_snake(cls.__name__),
            cascade="all, delete-orphan",
            lazy="selectin"
        )
    
    @property
    def titular_actual(self):
        """Titular actual (sin fecha_fin)"""
        return next(
            (t for t in self.titulares if t.fecha_fin is None),
            None
        )
    
    @property
    def tiene_titular(self) -> bool:
        """¿Hay titular actualmente asignado?"""
        return self.titular_actual is not None
    
    @property
    def titulares_anteriores(self):
        """Lista de titulares históricos (con fecha_fin)"""
        return [t for t in self.titulares if t.fecha_fin is not None]