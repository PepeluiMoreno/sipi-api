
# app/db/mixins/direccion.py
from decimal import Decimal
from typing import TYPE_CHECKING, Optional
from sqlalchemy import String, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, declared_attr

if TYPE_CHECKING:
    from app.db.models.geografia import Provincia, Municipio, ComunidadAutonoma
    from app.db.models.tipologias import TipoVia

class DireccionMixin:
    """
    Mixin para datos de dirección geográfica.
    
    IMPORTANTE:
    - Este mixin define SOLO las columnas FK (tipo_via_id, comunidad_autonoma_id, provincia_id, municipio_id)
    - NO define las relaciones (tipo_via, comunidad_autonoma, provincia, municipio)
    - Cada clase que herede este mixin debe definir sus propias relaciones con nombres descriptivos
    
    EJEMPLO DE USO:
    
    class Tecnico(DireccionMixin, Base):
        # ... otros campos ...
        
        # ✅ Definir relación con nombre descriptivo
        municipio_trabajo: Mapped["Municipio"] = relationship(
            "Municipio",
            primaryjoin="foreign(Tecnico.municipio_id) == Municipio.id",
            back_populates="tecnicos"
        )
    """
    
    # Componentes de dirección
    tipo_via_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("tipos_via.id"), index=True)
    nombre_via: Mapped[Optional[str]] = mapped_column(String(255))
    numero: Mapped[Optional[str]] = mapped_column(String(10))
    bloque: Mapped[Optional[str]] = mapped_column(String(10))
    escalera: Mapped[Optional[str]] = mapped_column(String(10))
    piso: Mapped[Optional[str]] = mapped_column(String(10))
    puerta: Mapped[Optional[str]] = mapped_column(String(10))
    codigo_postal: Mapped[Optional[str]] = mapped_column(String(10), index=True)
    
    # Referencias geográficas - SOLO FKs
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("comunidades_autonomas.id"), index=True)
    provincia_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("provincias.id"), index=True)
    municipio_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("municipios.id"), index=True)  # ✅ CORREGIDO: municipios.id (minúscula)
    
    # Coordenadas
    latitud: Mapped[Optional[Decimal]] = mapped_column(Float(precision=10, asdecimal=True), nullable=True)
    longitud: Mapped[Optional[Decimal]] = mapped_column(Float(precision=10, asdecimal=True), nullable=True)
    
    # ⚠️ NO DEFINIR RELACIONES AQUÍ
    # Las relaciones tipo_via, comunidad_autonoma, provincia y municipio
    # deben definirse en cada clase con nombres descriptivos.
    #
    # ANTES (❌ causaba conflictos):
    # @declared_attr
    # def Municipio(cls) -> Mapped[Optional["Municipio"]]:
    #     return relationship("Municipio", lazy="joined")
    #
    # AHORA (✅ cada clase define su propia relación):
    # En Tecnico: municipio_trabajo
    # En Adquiriente: municipio_residencia
    # En Notaria: municipio_ubicacion
    # etc.
    
    # Propiedades calculadas - NOTA: Estas propiedades ya no funcionarán
    # porque no hay relaciones. Debes acceder a través de las relaciones
    # específicas de cada clase (ej: tecnico.municipio_trabajo.nombre)
    
    @property
    def direccion_corta(self) -> str:
        """Dirección corta: tipo vía + nombre + número"""
        partes = []
        # Nota: tipo_via ya no está disponible aquí
        if self.nombre_via:
            partes.append(self.nombre_via)
        if self.numero:
            partes.append(f", {self.numero}")
        return "".join(partes).strip()