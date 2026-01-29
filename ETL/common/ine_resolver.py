# ETL/common/ine_resolver.py
"""
Módulo de resolución geográfica usando códigos INE.
Proporciona mapeos bidireccionales: codigo_ine <-> UUID

Uso:
    resolver = INEResolver()
    await resolver.cargar_desde_bd(session)

    # Resolver por codigo_ine
    ccaa_uuid, prov_uuid, muni_uuid = resolver.resolver_completo("28079")

    # Fallback por nombre (compatibilidad)
    codigo_ine = resolver.buscar_codigo_por_nombre("Madrid", "Madrid")
"""

import re
import logging
from typing import Dict, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

from .ine_constants import (
    PROVINCIA_A_CCAA,
    ALIAS_PROVINCIAS,
    ALIAS_MUNICIPIOS,
)

logger = logging.getLogger(__name__)


@dataclass
class CodigosINE:
    """Estructura para almacenar códigos INE de una ubicación"""
    ccaa: str       # 2 dígitos
    provincia: str  # 2 dígitos
    municipio: str  # 5 dígitos (provincia + municipio local)


class INEResolver:
    """
    Resuelve códigos INE a UUIDs de BD y viceversa.
    Carga mapeos desde BD o desde archivos CSV.
    """

    def __init__(self):
        # Mapeos codigo_ine -> UUID
        self.ccaa_ine_to_uuid: Dict[str, str] = {}
        self.provincia_ine_to_uuid: Dict[str, str] = {}
        self.municipio_ine_to_uuid: Dict[str, str] = {}

        # Mapeos inversos UUID -> codigo_ine
        self.ccaa_uuid_to_ine: Dict[str, str] = {}
        self.provincia_uuid_to_ine: Dict[str, str] = {}
        self.municipio_uuid_to_ine: Dict[str, str] = {}

        # Cache de nombres normalizados -> codigo_ine (para fallback)
        self.nombre_provincia_to_ine: Dict[str, str] = {}
        self.nombre_municipio_to_ine: Dict[Tuple[str, str], str] = {}  # (nombre, prov_ine) -> muni_ine

        # Estadísticas
        self.stats = {
            'ccaa_cargadas': 0,
            'provincias_cargadas': 0,
            'municipios_cargados': 0,
            'resoluciones_exitosas': 0,
            'resoluciones_fallback': 0,
            'resoluciones_fallidas': 0,
        }

    async def cargar_desde_bd(self, session) -> None:
        """
        Carga mapeos desde la base de datos.

        Args:
            session: Sesión de SQLAlchemy async
        """
        from sqlalchemy import select
        from sipi_core.models.geografia import ComunidadAutonoma, Provincia, Municipio

        logger.info("Cargando mapeos INE desde base de datos...")

        # Cargar Comunidades Autónomas
        result = await session.execute(select(ComunidadAutonoma))
        for ccaa in result.scalars().all():
            if ccaa.codigo_ine:
                codigo = ccaa.codigo_ine.zfill(2)
                self.ccaa_ine_to_uuid[codigo] = str(ccaa.id)
                self.ccaa_uuid_to_ine[str(ccaa.id)] = codigo
                self.stats['ccaa_cargadas'] += 1

        logger.info(f"  CCAA cargadas: {self.stats['ccaa_cargadas']}")

        # Cargar Provincias
        result = await session.execute(select(Provincia))
        for provincia in result.scalars().all():
            if provincia.codigo_ine:
                codigo = provincia.codigo_ine.zfill(2)
                self.provincia_ine_to_uuid[codigo] = str(provincia.id)
                self.provincia_uuid_to_ine[str(provincia.id)] = codigo

                # Cache por nombre
                nombre_norm = self._normalizar_nombre(provincia.nombre)
                self.nombre_provincia_to_ine[nombre_norm] = codigo
                if provincia.nombre_oficial:
                    nombre_oficial_norm = self._normalizar_nombre(provincia.nombre_oficial)
                    self.nombre_provincia_to_ine[nombre_oficial_norm] = codigo

                self.stats['provincias_cargadas'] += 1

        logger.info(f"  Provincias cargadas: {self.stats['provincias_cargadas']}")

        # Cargar Municipios
        result = await session.execute(select(Municipio))
        for municipio in result.scalars().all():
            if municipio.codigo_ine:
                codigo = municipio.codigo_ine.zfill(5)
                self.municipio_ine_to_uuid[codigo] = str(municipio.id)
                self.municipio_uuid_to_ine[str(municipio.id)] = codigo

                # Cache por nombre + provincia
                prov_ine = codigo[:2]
                nombre_norm = self._normalizar_nombre(municipio.nombre)
                self.nombre_municipio_to_ine[(nombre_norm, prov_ine)] = codigo
                if municipio.nombre_oficial:
                    nombre_oficial_norm = self._normalizar_nombre(municipio.nombre_oficial)
                    self.nombre_municipio_to_ine[(nombre_oficial_norm, prov_ine)] = codigo

                self.stats['municipios_cargados'] += 1

        logger.info(f"  Municipios cargados: {self.stats['municipios_cargados']}")
        logger.info("Mapeos INE cargados correctamente")

    def cargar_desde_csv(self, csv_dir: Path) -> None:
        """
        Carga mapeos desde archivos CSV de geografía transformada.
        Útil cuando no hay acceso a BD.

        Args:
            csv_dir: Directorio con comunidades_autonomas.csv, provincias.csv, municipios.csv
        """
        import pandas as pd

        logger.info(f"Cargando mapeos INE desde CSV en {csv_dir}...")

        # CCAA
        ccaa_path = csv_dir / 'comunidades_autonomas.csv'
        if ccaa_path.exists():
            df = pd.read_csv(ccaa_path, dtype=str)
            for _, row in df.iterrows():
                if 'codigo_ine' in row and 'id' in row:
                    codigo = str(row['codigo_ine']).zfill(2)
                    uuid_val = str(row['id'])
                    self.ccaa_ine_to_uuid[codigo] = uuid_val
                    self.ccaa_uuid_to_ine[uuid_val] = codigo
                    self.stats['ccaa_cargadas'] += 1

        # Provincias
        prov_path = csv_dir / 'provincias.csv'
        if prov_path.exists():
            df = pd.read_csv(prov_path, dtype=str)
            for _, row in df.iterrows():
                if 'codigo_ine' in row and 'id' in row:
                    codigo = str(row['codigo_ine']).zfill(2)
                    uuid_val = str(row['id'])
                    self.provincia_ine_to_uuid[codigo] = uuid_val
                    self.provincia_uuid_to_ine[uuid_val] = codigo

                    if 'nombre' in row:
                        nombre_norm = self._normalizar_nombre(str(row['nombre']))
                        self.nombre_provincia_to_ine[nombre_norm] = codigo

                    self.stats['provincias_cargadas'] += 1

        # Municipios
        muni_path = csv_dir / 'municipios.csv'
        if muni_path.exists():
            df = pd.read_csv(muni_path, dtype=str)
            for _, row in df.iterrows():
                if 'codigo_ine' in row and 'id' in row:
                    codigo = str(row['codigo_ine']).zfill(5)
                    uuid_val = str(row['id'])
                    self.municipio_ine_to_uuid[codigo] = uuid_val
                    self.municipio_uuid_to_ine[uuid_val] = codigo

                    if 'nombre' in row:
                        prov_ine = codigo[:2]
                        nombre_norm = self._normalizar_nombre(str(row['nombre']))
                        self.nombre_municipio_to_ine[(nombre_norm, prov_ine)] = codigo

                    self.stats['municipios_cargados'] += 1

        logger.info(f"CSV cargados: {self.stats['ccaa_cargadas']} CCAA, "
                   f"{self.stats['provincias_cargadas']} provincias, "
                   f"{self.stats['municipios_cargados']} municipios")

    def _normalizar_nombre(self, nombre: str) -> str:
        """Normaliza un nombre para comparación"""
        if not nombre:
            return ""

        nombre = str(nombre).upper().strip()

        # Quitar acentos
        reemplazos = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
            'À': 'A', 'È': 'E', 'Ì': 'I', 'Ò': 'O', 'Ù': 'U',
            'Ä': 'A', 'Ë': 'E', 'Ï': 'I', 'Ö': 'O', 'Ü': 'U',
            'Ñ': 'N', 'Ç': 'C',
        }
        for old, new in reemplazos.items():
            nombre = nombre.replace(old, new)

        # Quitar puntuación excepto espacios
        nombre = re.sub(r'[^\w\s]', ' ', nombre)

        # Normalizar espacios
        nombre = re.sub(r'\s+', ' ', nombre).strip()

        return nombre

    def resolver_ccaa(self, codigo_ine: str) -> Optional[str]:
        """
        Resuelve código INE de CCAA a UUID.

        Args:
            codigo_ine: Código INE de 2 dígitos

        Returns:
            UUID de la comunidad autónoma o None
        """
        return self.ccaa_ine_to_uuid.get(codigo_ine.zfill(2))

    def resolver_provincia(self, codigo_ine: str) -> Optional[str]:
        """
        Resuelve código INE de provincia a UUID.

        Args:
            codigo_ine: Código INE de 2 dígitos

        Returns:
            UUID de la provincia o None
        """
        return self.provincia_ine_to_uuid.get(codigo_ine.zfill(2))

    def resolver_municipio(self, codigo_ine: str) -> Optional[str]:
        """
        Resuelve código INE de municipio a UUID.

        Args:
            codigo_ine: Código INE de 5 dígitos

        Returns:
            UUID del municipio o None
        """
        return self.municipio_ine_to_uuid.get(codigo_ine.zfill(5))

    def derivar_provincia_de_municipio(self, codigo_municipio: str) -> str:
        """
        Extrae código provincia de código municipio INE.

        Args:
            codigo_municipio: Código de 5 dígitos

        Returns:
            Código de provincia (2 dígitos)
        """
        return codigo_municipio.zfill(5)[:2]

    def derivar_ccaa_de_provincia(self, codigo_provincia: str) -> Optional[str]:
        """
        Obtiene código CCAA a partir de código provincia.

        Args:
            codigo_provincia: Código de 2 dígitos

        Returns:
            Código de CCAA (2 dígitos) o None
        """
        return PROVINCIA_A_CCAA.get(codigo_provincia.zfill(2))

    def resolver_completo(self, codigo_municipio_ine: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Dado un código municipio INE (5 dígitos), resuelve los 3 UUIDs.

        Args:
            codigo_municipio_ine: Código INE del municipio (5 dígitos)

        Returns:
            Tupla (ccaa_uuid, provincia_uuid, municipio_uuid)
        """
        codigo_municipio = codigo_municipio_ine.zfill(5)
        codigo_provincia = self.derivar_provincia_de_municipio(codigo_municipio)
        codigo_ccaa = self.derivar_ccaa_de_provincia(codigo_provincia)

        ccaa_uuid = self.resolver_ccaa(codigo_ccaa) if codigo_ccaa else None
        provincia_uuid = self.resolver_provincia(codigo_provincia)
        municipio_uuid = self.resolver_municipio(codigo_municipio)

        if all([ccaa_uuid, provincia_uuid, municipio_uuid]):
            self.stats['resoluciones_exitosas'] += 1
        else:
            self.stats['resoluciones_fallidas'] += 1

        return (ccaa_uuid, provincia_uuid, municipio_uuid)

    def buscar_codigo_provincia_por_nombre(self, nombre_provincia: str) -> Optional[str]:
        """
        Busca código INE de provincia por nombre (fallback).

        Args:
            nombre_provincia: Nombre de la provincia

        Returns:
            Código INE (2 dígitos) o None
        """
        nombre_norm = self._normalizar_nombre(nombre_provincia)

        # 1. Búsqueda en alias conocidos
        if nombre_norm in ALIAS_PROVINCIAS:
            return ALIAS_PROVINCIAS[nombre_norm]

        # 2. Búsqueda en cache de BD
        if nombre_norm in self.nombre_provincia_to_ine:
            return self.nombre_provincia_to_ine[nombre_norm]

        # 3. Búsqueda parcial
        for nombre_bd, codigo in self.nombre_provincia_to_ine.items():
            if nombre_norm in nombre_bd or nombre_bd in nombre_norm:
                return codigo

        return None

    def buscar_codigo_municipio_por_nombre(
        self,
        nombre_municipio: str,
        nombre_provincia: str
    ) -> Optional[str]:
        """
        Busca código INE de municipio por nombre y provincia (fallback).

        Args:
            nombre_municipio: Nombre del municipio
            nombre_provincia: Nombre de la provincia

        Returns:
            Código INE (5 dígitos) o None
        """
        # Primero resolver provincia
        codigo_provincia = self.buscar_codigo_provincia_por_nombre(nombre_provincia)
        if not codigo_provincia:
            return None

        nombre_muni_norm = self._normalizar_nombre(nombre_municipio)

        # 1. Búsqueda en alias conocidos
        clave_alias = (nombre_muni_norm, codigo_provincia)
        if clave_alias in ALIAS_MUNICIPIOS:
            return ALIAS_MUNICIPIOS[clave_alias]

        # 2. Búsqueda exacta en cache
        clave = (nombre_muni_norm, codigo_provincia)
        if clave in self.nombre_municipio_to_ine:
            self.stats['resoluciones_fallback'] += 1
            return self.nombre_municipio_to_ine[clave]

        # 3. Búsqueda parcial en la provincia
        for (nombre_bd, prov_ine), codigo in self.nombre_municipio_to_ine.items():
            if prov_ine == codigo_provincia:
                if nombre_muni_norm in nombre_bd or nombre_bd in nombre_muni_norm:
                    self.stats['resoluciones_fallback'] += 1
                    return codigo

        return None

    def resolver_por_nombre(
        self,
        nombre_municipio: str,
        nombre_provincia: str
    ) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Resuelve UUIDs usando nombres (método de compatibilidad).
        Intenta encontrar el código INE por nombre y luego resuelve.

        Args:
            nombre_municipio: Nombre del municipio
            nombre_provincia: Nombre de la provincia

        Returns:
            Tupla (ccaa_uuid, provincia_uuid, municipio_uuid)
        """
        codigo_municipio = self.buscar_codigo_municipio_por_nombre(
            nombre_municipio,
            nombre_provincia
        )

        if codigo_municipio:
            return self.resolver_completo(codigo_municipio)

        self.stats['resoluciones_fallidas'] += 1
        return (None, None, None)

    def obtener_codigos_ine(self, municipio_uuid: str) -> Optional[CodigosINE]:
        """
        Dado un UUID de municipio, obtiene todos los códigos INE.

        Args:
            municipio_uuid: UUID del municipio

        Returns:
            CodigosINE o None
        """
        codigo_muni = self.municipio_uuid_to_ine.get(municipio_uuid)
        if not codigo_muni:
            return None

        codigo_prov = self.derivar_provincia_de_municipio(codigo_muni)
        codigo_ccaa = self.derivar_ccaa_de_provincia(codigo_prov)

        if not codigo_ccaa:
            return None

        return CodigosINE(
            ccaa=codigo_ccaa,
            provincia=codigo_prov,
            municipio=codigo_muni
        )

    def get_stats(self) -> Dict:
        """Devuelve estadísticas de uso"""
        return self.stats.copy()
