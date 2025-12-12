# models/figuras_proteccion.py

from __future__ import annotations
import enum
from typing import TYPE_CHECKING, Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, Index, CheckConstraint, Enum as SQLEnum
import strawberry

from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

@strawberry.enum
class NivelProteccion(str, enum.Enum):
    """
    Niveles jerárquicos de protección del patrimonio
    """
    NACIONAL = "nacional"      # BIC - Ámbito estatal (todas las CCAA)
    AUTONOMICO = "autonomico"  # Figuras autonómicas (BRL, BCIL, BIPA, etc.)
    LOCAL = "local"            # Catálogos municipales y protección local


class FiguraProteccion(UUIDPKMixin, AuditMixin, Base):
    """
    Figura de protección patrimonial según legislación española
    
    Las figuras de protección tienen diferentes denominaciones según la CCAA:
    
    NIVEL NACIONAL (comunidad_autonoma_id = NULL):
    - BIC (Bien de Interés Cultural) - Ley 16/1985
    - Patrimonio Inventariado
    
    NIVEL AUTONÓMICO (comunidad_autonoma_id = específico):
    - BRL (Comunitat Valenciana)
    - BCIL (Cataluña)
    - BIPA (Andalucía)
    - Bien Catalogado (Galicia, Murcia, etc.)
    - etc.
    
    NIVEL LOCAL:
    - Catálogos Municipales
    - Protección urbanística local
    """
    __tablename__ = "tipos_figura_proteccion"
    
    # =======================================================================
    # CAMPOS PRINCIPALES (ajustados al CSV)
    # =======================================================================
    
    # Código único identificador (ej: "BIC", "BRL", "BCIL", "BIPA")
    codigo: Mapped[str] = mapped_column(
        String(20), 
        index=True,
        nullable=False,
        comment="Código identificador de la figura (BIC, BRL, BCIL, etc.)"
    )
    
    # Denominación corta
    denominacion: Mapped[str] = mapped_column(
        String(255), 
        index=True,
        nullable=False,
        comment="Denominación oficial corta"
    )
    
    # Denominación completa
    denominacion_completa: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Denominación oficial completa"
    )
    
    # Descripción detallada
    descripcion: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Descripción de la figura de protección"
    )
    
    # Nivel jerárquico de protección
    nivel: Mapped[NivelProteccion] = mapped_column(
        SQLEnum(NivelProteccion, name='nivel_proteccion'),
        index=True,
        nullable=False,
        comment="Nivel de protección: nacional, autonomico o local"
    )
    
    # Orden de prioridad (1 = más importante)
    orden: Mapped[int] = mapped_column(
        Integer, 
        default=999,
        nullable=False,
        comment="Orden de prioridad para ordenar listados (1=más importante)"
    )
    
    # Normativa que la regula
    normativa: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Normativa legal que regula esta figura"
    )
    
    # URL a la normativa
    url_normativa: Mapped[Optional[str]] = mapped_column(
        String(500),
        comment="URL a la ley o normativa reguladora"
    )
    
    # Estado activo/inactivo
    activo: Mapped[bool] = mapped_column(
        Boolean, 
        default=True, 
        index=True,
        nullable=False,
        comment="Indica si la figura está vigente"
    )
    
    # =======================================================================
    # RELACIÓN CON COMUNIDAD AUTÓNOMA
    # =======================================================================
    
    # CCAA donde aplica esta figura (NULL = ámbito nacional)
    comunidad_autonoma_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("comunidades_autonomas.id"),
        index=True,
        nullable=True,
        comment="NULL = figura de ámbito nacional. Con valor = figura autonómica específica"
    )
    
    # Relación con CCAA
    comunidad_autonoma: Mapped[Optional["ComunidadAutonoma"]] = relationship(
        "ComunidadAutonoma",
        back_populates="figuras_proteccion"
    )
    
    # =======================================================================
    # RELACIONES
    # =======================================================================
    
    inmuebles: Mapped[list["Inmueble"]] = relationship(
        "Inmueble",
        back_populates="figura_proteccion"
    )
    
    # =======================================================================
    # CONSTRAINTS E ÍNDICES
    # =======================================================================
    
    __table_args__ = (
        # Constraint: nivel NACIONAL => comunidad_autonoma_id DEBE ser NULL
        CheckConstraint(
            "(nivel != 'nacional') OR (comunidad_autonoma_id IS NULL)",
            name="ck_nacional_sin_ccaa"
        ),
        # Constraint: nivel AUTONOMICO => comunidad_autonoma_id DEBE tener valor
        CheckConstraint(
            "(nivel != 'autonomico') OR (comunidad_autonoma_id IS NOT NULL)",
            name="ck_autonomico_con_ccaa"
        ),
        # Índice único compuesto: mismo código puede existir en diferentes CCAA
        # pero no puede repetirse código+ccaa (permite BRL en Valencia pero no dos BRL en Valencia)
        Index(
            'uq_codigo_ccaa',
            'codigo',
            'comunidad_autonoma_id',
            unique=True
        ),
        # Índice para búsquedas por nivel
        Index('ix_figura_nivel', 'nivel'),
        # Índice para búsquedas por activo
        Index('ix_figura_activo', 'activo'),
    )
    
    # =======================================================================
    # PROPIEDADES CALCULADAS
    # =======================================================================
    
    @property
    def es_nacional(self) -> bool:
        """Indica si es una figura de ámbito nacional"""
        return self.nivel == NivelProteccion.NACIONAL
    
    @property
    def es_autonomica(self) -> bool:
        """Indica si es una figura de ámbito autonómico"""
        return self.nivel == NivelProteccion.AUTONOMICO
    
    @property
    def es_local(self) -> bool:
        """Indica si es una figura de ámbito local"""
        return self.nivel == NivelProteccion.LOCAL
    
    @property
    def ambito(self) -> str:
        """Descripción del ámbito territorial"""
        if self.es_nacional:
            return "Nacional (todas las CCAA)"
        elif self.comunidad_autonoma:
            return self.comunidad_autonoma.nombre
        return "Local/Municipal"
    
    @property
    def denominacion_con_ambito(self) -> str:
        """Denominación completa con ámbito territorial"""
        if self.es_nacional:
            return f"{self.denominacion} (Nacional)"
        elif self.comunidad_autonoma:
            return f"{self.denominacion} ({self.comunidad_autonoma.codigo})"
        return self.denominacion
    
    @property
    def codigo_completo(self) -> str:
        """Código con sufijo de CCAA si aplica"""
        if self.comunidad_autonoma:
            return f"{self.codigo}_{self.comunidad_autonoma.codigo}"
        return self.codigo
    
    def __repr__(self) -> str:
        return f"<TipoFiguraProteccion {self.codigo} - {self.denominacion} ({self.nivel})>"