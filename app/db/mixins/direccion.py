# app/db/mixins/direccion.py
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, declared_attr

if TYPE_CHECKING:
    from app.db.models.geografia import Provincia, Municipio, ComunidadAutonoma
    from app.db.models.tipologias import TipoVia

class DireccionMixin:
    """Mixin para datos de dirección geográfica"""
    
    # Componentes de dirección
    tipo_via_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_via.id"), index=True)
    nombre_via: Mapped[Optional[str]] = mapped_column(String(255))
    numero: Mapped[Optional[str]] = mapped_column(String(10))
    bloque: Mapped[Optional[str]] = mapped_column(String(10))
    escalera: Mapped[Optional[str]] = mapped_column(String(10))
    piso: Mapped[Optional[str]] = mapped_column(String(10))
    puerta: Mapped[Optional[str]] = mapped_column(String(10))
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    
    # Referencias geográficas
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True)
    provincia_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    Municipio_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("Municipio.id"), index=True)
    
    # Coordenadas
    latitud: Mapped[Optional[Decimal]] = mapped_column(Float(precision=10, asdecimal=True), nullable=True)
    longitud: Mapped[Optional[Decimal]] = mapped_column(Float(precision=10, asdecimal=True), nullable=True)
    
    # Relaciones (declaradas correctamente)
    @declared_attr
    def tipo_via(cls) -> Mapped[Optional["TipoVia"]]:
        return relationship("TipoVia", lazy="joined")
    
    @declared_attr
    def comunidad_autonoma(cls) -> Mapped[Optional["ComunidadAutonoma"]]:
        return relationship("ComunidadAutonoma", lazy="joined")
    
    @declared_attr
    def provincia(cls) -> Mapped[Optional["Provincia"]]:
        return relationship("Provincia", lazy="joined")
    
    @declared_attr
    def Municipio(cls) -> Mapped[Optional["Municipio"]]:
        return relationship("Municipio", lazy="joined")
    
    @property
    def direccion_completa(self) -> str:
        """Dirección completa formateada"""
        partes = []
        
        if self.tipo_via and self.nombre_via:
            partes.append(f"{self.tipo_via.nombre} {self.nombre_via}")
        elif self.nombre_via:
            partes.append(self.nombre_via)
        
        if self.numero:
            partes.append(f", nº {self.numero}")
        
        detalles = []
        for label, valor in [
            ("Bloque", self.bloque),
            ("Esc.", self.escalera),
            ("Piso", self.piso),
            ("Puerta", self.puerta)
        ]:
            if valor:
                detalles.append(f"{label} {valor}")
        
        if detalles:
            partes.append(f" ({', '.join(detalles)})")
        
        if self.codigo_postal and self.Municipio:
            partes.append(f" - {self.codigo_postal} {self.Municipio.nombre}")
        elif self.codigo_postal:
            partes.append(f" - {self.codigo_postal}")
        elif self.Municipio:
            partes.append(f" - {self.Municipio.nombre}")
        
        return "".join(partes).strip()
    
    @property
    def direccion_corta(self) -> str:
        """Dirección corta: tipo vía + nombre + número"""
        partes = []
        if self.tipo_via and self.nombre_via:
            partes.append(f"{self.tipo_via.nombre} {self.nombre_via}")
        elif self.nombre_via:
            partes.append(self.nombre_via)
        if self.numero:
            partes.append(f", {self.numero}")
        return "".join(partes).strip()
