#!/usr/bin/env python3
"""
transform_registradores.py - Usa INEResolver para resolución geográfica por código INE.
"""

import sys
import csv
import os
import logging
import glob
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import uuid
import json
from pathlib import Path

# Importar el sistema de conexión
from sipi_core.db.sessions.async_session import db_manager
from sqlalchemy import select
import asyncio

# Agregar path para módulo common
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from common.ine_resolver import INEResolver

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CSVTransformer:
    """Transformador de CSV usando INEResolver para resolución geográfica"""

    def __init__(self):
        # Resolver INE para resolución geográfica
        self.ine_resolver = INEResolver()

        self.stats = {
            'total': 0,
            'ok': 0,
            'error': 0,
            'provincias_no_encontradas': [],
            'municipios_no_encontrados': [],
            'resoluciones_por_ine': 0,
            'resoluciones_por_nombre': 0,
        }
    
    async def cargar_datos_geograficos(self):
        """Carga mapeos INE desde la BD usando INEResolver"""
        logger.info("📥 Cargando datos geográficos con INEResolver...")

        try:
            async with db_manager.session() as session:
                await self.ine_resolver.cargar_desde_bd(session)

                stats = self.ine_resolver.get_stats()
                logger.info(f"  ✅ {stats['ccaa_cargadas']} CCAA cargadas")
                logger.info(f"  ✅ {stats['provincias_cargadas']} provincias cargadas")
                logger.info(f"  ✅ {stats['municipios_cargados']} municipios cargados")

        except Exception as e:
            logger.error(f"❌ Error cargando datos geográficos: {e}")
            raise
    
    def resolver_geografia(
        self,
        nombre_municipio: str,
        nombre_provincia: str,
        codigo_ine_municipio: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        """
        Resuelve geografía usando código INE (preferido) o nombres (fallback).

        Args:
            nombre_municipio: Nombre del municipio
            nombre_provincia: Nombre de la provincia
            codigo_ine_municipio: Código INE del municipio (5 dígitos) si está disponible

        Returns:
            Tupla (ccaa_uuid, provincia_uuid, municipio_uuid, codigo_ine_usado)
        """
        # 1. Si tenemos código INE, usar resolución directa
        if codigo_ine_municipio:
            ccaa_uuid, prov_uuid, muni_uuid = self.ine_resolver.resolver_completo(codigo_ine_municipio)
            if muni_uuid:
                self.stats['resoluciones_por_ine'] += 1
                return (ccaa_uuid, prov_uuid, muni_uuid, codigo_ine_municipio)

        # 2. Fallback: resolver por nombre
        ccaa_uuid, prov_uuid, muni_uuid = self.ine_resolver.resolver_por_nombre(
            nombre_municipio,
            nombre_provincia
        )

        if muni_uuid:
            self.stats['resoluciones_por_nombre'] += 1
            # Obtener el código INE usado
            codigo_ine = self.ine_resolver.municipio_uuid_to_ine.get(muni_uuid)
            return (ccaa_uuid, prov_uuid, muni_uuid, codigo_ine)

        # No encontrado - registrar en stats
        if nombre_provincia.upper() not in self.stats['provincias_no_encontradas']:
            # Verificar si es problema de provincia
            codigo_prov = self.ine_resolver.buscar_codigo_provincia_por_nombre(nombre_provincia)
            if not codigo_prov:
                self.stats['provincias_no_encontradas'].append(nombre_provincia.upper())

        error_key = f"{nombre_municipio.upper()} ({nombre_provincia.upper()})"
        if error_key not in self.stats['municipios_no_encontrados']:
            self.stats['municipios_no_encontrados'].append(error_key)

        return (None, None, None, None)
    
    def leer_csv(self, file_path: str) -> List[Dict]:
        """Lee CSV con manejo robusto de encoding"""
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    # Leer un poco para detectar delimitador
                    sample = f.read(1024)
                    f.seek(0)
                    
                    # Detectar delimitador
                    if ';' in sample and sample.count(';') > sample.count(','):
                        delimiter = ';'
                    else:
                        delimiter = ','
                    
                    # Leer CSV
                    reader = csv.DictReader(f, delimiter=delimiter)
                    data = list(reader)
                    
                    logger.info(f"✅ CSV leído con encoding: {encoding}, delimitador: '{delimiter}'")
                    
                    # Mostrar campos disponibles
                    if reader.fieldnames:
                        logger.info(f"  Campos disponibles: {', '.join(reader.fieldnames)}")
                    
                    return data
                    
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Encoding {encoding} falló: {e}")
                continue
        
        raise ValueError(f"No se pudo leer el CSV con ningún encoding")
    
    def procesar_csv(self, input_file: str, output_file: str):
        """Procesa el archivo CSV"""
        logger.info(f"📄 Procesando: {input_file}")
        
        try:
            # Leer CSV
            data = self.leer_csv(input_file)
            logger.info(f"  Filas encontradas: {len(data)}")
            
            # Procesar cada fila
            filas_procesadas = []
            
            for idx, fila in enumerate(data, 1):
                self.stats['total'] += 1
                
                try:
                    # Normalizar nombres de columnas
                    fila_normalizada = {}
                    for key, value in fila.items():
                        key_norm = key.strip().lower()
                        fila_normalizada[key_norm] = value
                    
                    # Obtener datos con diferentes nombres posibles
                    nombre = self._obtener_valor(fila_normalizada, 
                                                ['nombre', 'nombre registro', 'registro', 'denominacion'])
                    
                    municipio = self._obtener_valor(fila_normalizada,
                                                   ['municipio', 'localidad', 'municipio/s', 'poblacion'])

                    # Si no hay municipio directo, extraerlo de la URL
                    if not municipio:
                        url = self._obtener_valor(fila_normalizada, ['url'])
                        if url:
                            # URL format: .../propiedad/{provincia}/{municipio}/registro-...
                            parts = url.rstrip('/').split('/')
                            if len(parts) >= 3:
                                # municipio está en posición -2 (antes del nombre del registro)
                                municipio_slug = parts[-2]
                                # Convertir slug a nombre (ej: "donostia-san-sebastian" -> "Donostia-San Sebastián")
                                municipio = municipio_slug.replace('-', ' ').title()

                    provincia = self._obtener_valor(fila_normalizada,
                                                   ['provincia', 'provincia/s', 'prov'])
                    
                    if not nombre:
                        self.stats['error'] += 1
                        logger.warning(f"  Fila {idx}: Sin nombre")
                        continue
                    
                    if not municipio:
                        self.stats['error'] += 1
                        logger.warning(f"  Fila {idx}: Sin municipio")
                        continue
                    
                    if not provincia:
                        self.stats['error'] += 1
                        logger.warning(f"  Fila {idx}: Sin provincia")
                        continue
                    
                    # Buscar IDs geográficos usando INEResolver
                    codigo_ine_csv = self._obtener_valor(fila_normalizada,
                                                         ['codigo_ine_municipio', 'codigo_ine', 'ine'])

                    ccaa_uuid, prov_uuid, municipio_id, codigo_ine_usado = self.resolver_geografia(
                        municipio,
                        provincia,
                        codigo_ine_csv if codigo_ine_csv else None
                    )

                    if not municipio_id:
                        self.stats['error'] += 1
                        logger.warning(f"  Fila {idx}: No encontrado '{municipio}' en '{provincia}'")
                        continue

                    # Derivar códigos INE
                    codigo_ine_prov = codigo_ine_usado[:2] if codigo_ine_usado else ''
                    codigo_ine_ccaa = self.ine_resolver.derivar_ccaa_de_provincia(codigo_ine_prov) if codigo_ine_prov else ''

                    # Crear fila procesada
                    fila_procesada = {
                        'id': str(uuid.uuid4()),
                        'nombre': nombre.strip(),
                        'identificacion': self._obtener_valor(fila_normalizada,
                                                            ['identificacion', 'cif', 'nif', 'dni']).strip(),
                        'tipo_identificacion_id': 'NIF',
                        'direccion': self._obtener_valor(fila_normalizada,
                                                        ['direccion', 'domicilio', 'calle']).strip(),
                        'codigo_postal': self._obtener_valor(fila_normalizada,
                                                            ['codigo_postal', 'cp', 'codigo postal']).strip(),
                        'telefono': self._obtener_valor(fila_normalizada,
                                                       ['telefono', 'tel', 'telefono/s']).strip(),
                        'email': self._obtener_valor(fila_normalizada,
                                                    ['email', 'correo', 'e-mail']).strip(),
                        'municipio_id': municipio_id,
                        'codigo_ine_ccaa': codigo_ine_ccaa,
                        'codigo_ine_provincia': codigo_ine_prov,
                        'codigo_ine_municipio': codigo_ine_usado or '',
                        'audit_creado_en': datetime.utcnow().isoformat(),
                        'audit_creado_por': 'transform_registradores.py',
                    }
                    
                    filas_procesadas.append(fila_procesada)
                    self.stats['ok'] += 1
                    
                    # Mostrar progreso cada 50 filas
                    if idx % 50 == 0:
                        logger.info(f"  Procesadas {idx}/{len(data)} filas")
                    
                except Exception as e:
                    self.stats['error'] += 1
                    logger.error(f"  Fila {idx}: Error {e}")
            
            # Escribir CSV de salida
            if filas_procesadas:
                campos = [
                    'id', 'nombre', 'identificacion', 'tipo_identificacion_id',
                    'direccion', 'codigo_postal', 'telefono', 'email',
                    'municipio_id', 'codigo_ine_ccaa', 'codigo_ine_provincia', 'codigo_ine_municipio',
                    'audit_creado_en', 'audit_creado_por'
                ]
                
                os.makedirs(os.path.dirname(output_file), exist_ok=True)
                
                with open(output_file, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=campos)
                    writer.writeheader()
                    writer.writerows(filas_procesadas)
                
                logger.info(f"✅ Guardado: {output_file}")
                logger.info(f"  Filas procesadas: {len(filas_procesadas)}")
                
                # Generar reporte
                self.generar_reporte(input_file, output_file)
            else:
                logger.warning("⚠️ No se procesaron filas")
                
        except Exception as e:
            logger.error(f"❌ Error procesando CSV: {e}")
            raise
    
    def _obtener_valor(self, fila: Dict, posibles_claves: List[str]) -> str:
        """Obtiene un valor de la fila probando diferentes nombres de clave"""
        for clave in posibles_claves:
            valor = fila.get(clave)
            if valor and str(valor).strip():
                return str(valor).strip()
        return ""
    
    def generar_reporte(self, input_file: str, output_file: str):
        """Genera un reporte JSON"""
        reporte_file = output_file.replace('.csv', '_REPORTE.json')
        
        reporte = {
            'fecha': datetime.now().isoformat(),
            'archivo_origen': input_file,
            'archivo_destino': output_file,
            'estadisticas': self.stats,
            'provincias_no_encontradas': self.stats['provincias_no_encontradas'],
            'municipios_no_encontrados': self.stats['municipios_no_encontrados'][:20]
        }
        
        with open(reporte_file, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Reporte: {reporte_file}")


def encontrar_csv_mas_reciente(directorio: str) -> Optional[str]:
    """Encuentra el CSV más reciente"""
    archivos = glob.glob(os.path.join(directorio, "registros_propiedad_*.csv"))
    
    if not archivos:
        return None
    
    def extraer_fecha(ruta: str):
        nombre = os.path.basename(ruta)
        match = re.search(r'registros_propiedad_(\d{8})_(\d{6})', nombre)
        if match:
            return match.group(1) + match.group(2)
        return "0"
    
    archivos.sort(key=extraer_fecha, reverse=True)
    return archivos[0]


async def main_async():
    """Función principal async"""
    # Directorios
    script_dir = os.path.dirname(os.path.abspath(__file__))
    extract_dir = os.path.join(script_dir, '../extract')
    transform_dir = os.path.join(script_dir, '../transform')
    
    # Buscar CSV más reciente
    csv_path = encontrar_csv_mas_reciente(extract_dir)
    if not csv_path:
        logger.error(f"❌ No hay CSVs en {extract_dir}")
        logger.info(f"  Buscando en: {extract_dir}")
        
        # Listar archivos para ayudar en debugging
        archivos = os.listdir(extract_dir)
        if archivos:
            logger.info("  Archivos encontrados:")
            for archivo in archivos[:10]:
                logger.info(f"    - {archivo}")
        return
    
    logger.info(f"📂 CSV encontrado: {csv_path}")
    
    # Crear transformador
    transformer = CSVTransformer()
    
    try:
        # Cargar datos geográficos
        await transformer.cargar_datos_geograficos()
        
        # Generar nombre de salida
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(transform_dir, exist_ok=True)
        output_path = os.path.join(transform_dir, f"registros_propiedad_transformado_{timestamp}.csv")
        
        # Procesar
        transformer.procesar_csv(csv_path, output_path)
        
        # Mostrar resumen
        logger.info("=" * 50)
        logger.info("RESUMEN:")
        logger.info(f"  Total filas: {transformer.stats['total']}")
        logger.info(f"  ✅ Procesadas: {transformer.stats['ok']}")
        logger.info(f"  Resoluciones por código INE: {transformer.stats['resoluciones_por_ine']}")
        logger.info(f"  Resoluciones por nombre (fallback): {transformer.stats['resoluciones_por_nombre']}")
        logger.info(f"  ❌ Errores: {transformer.stats['error']}")
        
        if transformer.stats['provincias_no_encontradas']:
            logger.info(f"  Provincias no encontradas: {len(transformer.stats['provincias_no_encontradas'])}")
            for prov in transformer.stats['provincias_no_encontradas'][:10]:
                logger.info(f"    - {prov}")
        
        if transformer.stats['municipios_no_encontrados']:
            logger.info(f"  Municipios no encontrados: {len(transformer.stats['municipios_no_encontrados'])}")
            for muni in transformer.stats['municipios_no_encontrados'][:10]:
                logger.info(f"    - {muni}")
        
        logger.info("=" * 50)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Función principal"""
    logger.info("=" * 60)
    logger.info("TRANSFORMADOR DE REGISTROS DE PROPIEDAD")
    logger.info("=" * 60)
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\n🛑 Proceso interrumpido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()