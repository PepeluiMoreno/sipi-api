# app/db/mixins/identificacion.py
import enum
import strawberry
from typing import Optional
from sqlalchemy import String, Enum
from sqlalchemy.orm import Mapped, mapped_column

@strawberry.enum
class TipoIdentificacion(str, enum.Enum):
    """Tipos de documento de identidad"""
    DNI = "dni"
    NIE = "nie"
    NIF = "nif"
    CIF = "cif"
    PASAPORTE = "pasaporte"
    CIF_EXTRANJERO = "cif_extranjero"
    OTRO = "otro"

class IdentificacionMixin:
    """Mixin unificado para identificación de personas (físicas y jurídicas)"""
    
    tipo_identificacion: Mapped[Optional[TipoIdentificacion]] = mapped_column(Enum(TipoIdentificacion), index=True)
    identificacion: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    nombre: Mapped[str] = mapped_column(String(255))  # Campo unificado
   
    # Campos específicos para persona física
    apellidos: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    
    # Campo específico para persona jurídica
    identificacion_extranjera: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
       
    @property
    def nombre_completo(self) -> str:
        """Nombre completo formateado según tipo de persona"""
        if self.apellidos:
            return f"{self.nombre} {self.apellidos}"
        return self.nombre