# transform_notarios.py
"""
Transforma CSV de notarios a dos tablas: notarias y notarias_titulares
Usa INEResolver para resolución geográfica por código INE.
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

# Importar el sistema de conexión y el resolver INE
from sipi.db.sessions.async_session import db_manager
from sqlalchemy import select
import asyncio

# Agregar path para módulo common
sys.path.insert(0, str(Path(__file__).parent.parent))
from common.ine_resolver import INEResolver

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransformadorNotarios:
    """Transforma CSV de notarios a dos tablas relacionadas usando INEResolver"""

    def __init__(self):
        # Resolver INE para resolución geográfica
        self.ine_resolver = INEResolver()

        # Datos procesados
        self.notarias = {}  # codigo_notaria -> datos
        self.titulares = []  # lista de titulares

        self.stats = {
            'total_filas': 0,
            'notarias_creadas': 0,
            'titulares_creados': 0,
            'errores': 0,
            'provincias_no_encontradas': set(),
            'municipios_no_encontrados': set(),
            'codigos_notaria_duplicados': [],
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

        # No encontrado
        self.stats['municipios_no_encontrados'].add(
            f"{nombre_municipio.upper()} ({nombre_provincia.upper()})"
        )
        return (None, None, None, None)
    
    def leer_csv(self, file_path: str) -> List[Dict]:
        """Lee CSV con manejo robusto de encoding"""
        # utf-8-sig handles BOM automatically
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    sample = f.read(1024)
                    f.seek(0)
                    
                    delimiter = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
                    
                    reader = csv.DictReader(f, delimiter=delimiter)
                    data = list(reader)
                    
                    logger.info(f"✅ CSV leído: {encoding}, delimitador: '{delimiter}'")
                    if reader.fieldnames:
                        logger.info(f"  Campos: {', '.join(reader.fieldnames)}")
                    
                    return data
                    
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.warning(f"Encoding {encoding} falló: {e}")
                continue
        
        raise ValueError(f"No se pudo leer el CSV")
    
    def extraer_codigo_postal(self, direccion: str) -> Tuple[str, str]:
        """Extrae código postal de la dirección si está presente"""
        if not direccion:
            return "", ""
        
        # Buscar patrón: 5 dígitos al final o en medio
        match = re.search(r'\b(\d{5})\b', direccion)
        if match:
            cp = match.group(1)
            # Quitar CP de la dirección
            direccion_limpia = direccion.replace(cp, '').strip()
            # Limpiar espacios múltiples
            direccion_limpia = re.sub(r'\s+', ' ', direccion_limpia)
            return direccion_limpia, cp
        
        return direccion, ""
    
    def procesar_csv(self, input_file: str) -> Tuple[List[Dict], List[Dict]]:
        """Procesa CSV y genera datos para dos tablas"""
        logger.info(f"📄 Procesando: {input_file}")
        
        data = self.leer_csv(input_file)
        logger.info(f"  Filas: {len(data)}")
        
        for idx, fila in enumerate(data, 1):
            self.stats['total_filas'] += 1
            
            try:
                # Obtener datos de la fila
                apellidos_nombre = fila.get('apellidos_nombre', '').strip()
                direccion_original = fila.get('direccion', '').strip()
                municipio = fila.get('municipio', '').strip()
                provincia = fila.get('provincia', '').strip()
                telefono = fila.get('telefono', '').strip()
                fax = fila.get('fax', '').strip()
                email_personal = fila.get('email_personal', '').strip()
                email_corporativo = fila.get('email_corporativo', '').strip()
                email_notaria = fila.get('email_notaria', '').strip()
                estado = fila.get('estado', '').strip()
                codigo_ultimas_voluntades = fila.get('codigo_ultimas_voluntades', '').strip()
                codigo_notaria = fila.get('codigo_notaria', '').strip()
                idiomas_extranjeros = fila.get('idiomas_extranjeros', '').strip()
                
                # Validaciones básicas
                if not codigo_notaria:
                    logger.warning(f"  Fila {idx}: Sin código de notaría (skip)")
                    self.stats['errores'] += 1
                    continue
                
                if not apellidos_nombre:
                    logger.warning(f"  Fila {idx}: Sin apellidos_nombre (skip)")
                    self.stats['errores'] += 1
                    continue
                
                if not municipio or not provincia:
                    logger.warning(f"  Fila {idx}: Sin municipio/provincia (skip)")
                    self.stats['errores'] += 1
                    continue
                
                # Resolver geografía usando INEResolver
                # Intentar obtener codigo_ine del CSV si existe
                codigo_ine_csv = fila.get('codigo_ine_municipio', '').strip()

                ccaa_uuid, prov_uuid, municipio_id, codigo_ine_usado = self.resolver_geografia(
                    municipio,
                    provincia,
                    codigo_ine_csv if codigo_ine_csv else None
                )

                if not municipio_id:
                    logger.warning(f"  Fila {idx}: Municipio no encontrado: {municipio} ({provincia})")
                    self.stats['errores'] += 1
                    continue
                
                # Extraer código postal de la dirección
                direccion_limpia, codigo_postal = self.extraer_codigo_postal(direccion_original)
                
                # --- NOTARIA (tabla principal) ---
                if codigo_notaria not in self.notarias:
                    # Nueva notaría
                    notaria_id = str(uuid.uuid4())

                    # Derivar códigos INE de provincia y CCAA desde el código de municipio
                    codigo_ine_prov = codigo_ine_usado[:2] if codigo_ine_usado else ''
                    codigo_ine_ccaa = self.ine_resolver.derivar_ccaa_de_provincia(codigo_ine_prov) if codigo_ine_prov else ''

                    self.notarias[codigo_notaria] = {
                        'id': notaria_id,
                        'codigo_notaria': codigo_notaria,
                        'direccion': direccion_limpia,
                        'codigo_postal': codigo_postal,
                        'telefono': telefono,
                        'fax': fax,
                        'email': email_notaria,
                        'municipio_id': municipio_id,
                        'codigo_ine_ccaa': codigo_ine_ccaa,
                        'codigo_ine_provincia': codigo_ine_prov,
                        'codigo_ine_municipio': codigo_ine_usado or '',
                        'activa': True,  # Por defecto activa
                        'audit_creado_en': datetime.utcnow().isoformat(),
                        'audit_creado_por': 'transform_notarios.py',
                    }

                    self.stats['notarias_creadas'] += 1
                else:
                    # Notaría duplicada (mismo código)
                    self.stats['codigos_notaria_duplicados'].append(codigo_notaria)
                    notaria_id = self.notarias[codigo_notaria]['id']
                
                # --- TITULAR (tabla relacionada) ---
                titular = {
                    'id': str(uuid.uuid4()),
                    'apellidos_nombre': apellidos_nombre,
                    'email_personal': email_personal,
                    'email_corporativo': email_corporativo,
                    'codigo_ultimas_voluntades': codigo_ultimas_voluntades,
                    'idiomas_extranjeros': idiomas_extranjeros,
                    'estado': estado,
                    'notaria_id': notaria_id,  # FK a notarias
                    'fecha_inicio': datetime.utcnow().date().isoformat(),  # Por defecto hoy
                    'fecha_fin': None,  # Activo (sin fecha fin)
                    'audit_creado_en': datetime.utcnow().isoformat(),
                    'audit_creado_por': 'transform_notarios.py',
                }
                
                self.titulares.append(titular)
                self.stats['titulares_creados'] += 1
                
                # Progreso
                if idx % 100 == 0:
                    logger.info(f"  Procesadas {idx}/{len(data)} filas")
                
            except Exception as e:
                logger.error(f"  Fila {idx}: Error {e}")
                self.stats['errores'] += 1
        
        return list(self.notarias.values()), self.titulares
    
    def guardar_csvs(self, notarias: List[Dict], titulares: List[Dict], 
                     output_dir: str, timestamp: str):
        """Guarda dos CSVs: uno para notarias y otro para titulares"""
        
        os.makedirs(output_dir, exist_ok=True)
        
        # CSV 1: Notarias
        if notarias:
            notarias_file = os.path.join(output_dir, f"notarias_transformado_{timestamp}.csv")
            
            campos_notarias = [
                'id', 'codigo_notaria', 'direccion', 'codigo_postal',
                'telefono', 'fax', 'email', 'municipio_id',
                'codigo_ine_ccaa', 'codigo_ine_provincia', 'codigo_ine_municipio',
                'activa', 'audit_creado_en', 'audit_creado_por'
            ]
            
            with open(notarias_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=campos_notarias)
                writer.writeheader()
                writer.writerows(notarias)
            
            logger.info(f"✅ Notarias: {notarias_file} ({len(notarias)} registros)")
        
        # CSV 2: Titulares
        if titulares:
            titulares_file = os.path.join(output_dir, f"notarias_titulares_transformado_{timestamp}.csv")
            
            campos_titulares = [
                'id', 'apellidos_nombre', 'email_personal', 'email_corporativo',
                'codigo_ultimas_voluntades', 'idiomas_extranjeros', 'estado',
                'notaria_id', 'fecha_inicio', 'fecha_fin',
                'audit_creado_en', 'audit_creado_por'
            ]
            
            with open(titulares_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=campos_titulares)
                writer.writeheader()
                writer.writerows(titulares)
            
            logger.info(f"✅ Titulares: {titulares_file} ({len(titulares)} registros)")
    
    def generar_reporte(self, input_file: str, output_dir: str, timestamp: str):
        """Genera reporte JSON"""
        reporte_file = os.path.join(output_dir, f"notarios_transformacion_REPORTE_{timestamp}.json")
        
        reporte = {
            'fecha': datetime.now().isoformat(),
            'archivo_origen': input_file,
            'estadisticas': {
                'total_filas_csv': self.stats['total_filas'],
                'notarias_creadas': self.stats['notarias_creadas'],
                'titulares_creados': self.stats['titulares_creados'],
                'errores': self.stats['errores'],
                'codigos_duplicados': len(self.stats['codigos_notaria_duplicados'])
            },
            'provincias_no_encontradas': list(self.stats['provincias_no_encontradas']),
            'municipios_no_encontrados': list(self.stats['municipios_no_encontrados'])[:50],
            'codigos_notaria_duplicados': self.stats['codigos_notaria_duplicados'][:20]
        }
        
        with open(reporte_file, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📊 Reporte: {reporte_file}")


def encontrar_csv_mas_reciente(directorio: str, patron: str = "notarios_espana*.csv") -> Optional[str]:
    """Encuentra el CSV más reciente"""
    archivos = glob.glob(os.path.join(directorio, patron))
    
    if not archivos:
        return None
    
    # Ordenar por fecha de modificación
    archivos.sort(key=os.path.getmtime, reverse=True)
    return archivos[0]


async def main_async():
    """Función principal async"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Buscar CSV en el mismo directorio o en subdirectorio extract
    extract_dir = script_dir  # El CSV puede estar en el mismo directorio
    extract_subdir = os.path.join(script_dir, 'extract')
    transform_dir = os.path.join(script_dir, 'transform')
    
    # Buscar CSV - primero en el mismo directorio, luego en subdirectorio extract
    csv_path = encontrar_csv_mas_reciente(extract_dir)
    if not csv_path and os.path.exists(extract_subdir):
        csv_path = encontrar_csv_mas_reciente(extract_subdir)
    if not csv_path:
        logger.error(f"❌ No hay CSVs de notarios en {extract_dir} ni en {extract_subdir}")
        return
    
    logger.info(f"📂 CSV encontrado: {csv_path}")
    
    # Crear transformador
    transformador = TransformadorNotarios()
    
    try:
        # Cargar datos geográficos
        await transformador.cargar_datos_geograficos()
        
        # Procesar CSV
        notarias, titulares = transformador.procesar_csv(csv_path)
        
        # Guardar CSVs
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transformador.guardar_csvs(notarias, titulares, transform_dir, timestamp)
        
        # Generar reporte
        transformador.generar_reporte(csv_path, transform_dir, timestamp)
        
        # Resumen
        logger.info("=" * 70)
        logger.info("✅ TRANSFORMACIÓN COMPLETADA")
        logger.info("=" * 70)
        logger.info(f"  Total filas CSV: {transformador.stats['total_filas']}")
        logger.info(f"  Notarías creadas: {transformador.stats['notarias_creadas']}")
        logger.info(f"  Titulares creados: {transformador.stats['titulares_creados']}")
        logger.info(f"  Resoluciones por código INE: {transformador.stats['resoluciones_por_ine']}")
        logger.info(f"  Resoluciones por nombre (fallback): {transformador.stats['resoluciones_por_nombre']}")
        logger.info(f"  Errores: {transformador.stats['errores']}")
        
        if transformador.stats['provincias_no_encontradas']:
            logger.warning(f"  ⚠️ Provincias no encontradas: {len(transformador.stats['provincias_no_encontradas'])}")
            for prov in list(transformador.stats['provincias_no_encontradas'])[:5]:
                logger.warning(f"     - {prov}")
        
        if transformador.stats['municipios_no_encontrados']:
            logger.warning(f"  ⚠️ Municipios no encontrados: {len(transformador.stats['municipios_no_encontrados'])}")
            for muni in list(transformador.stats['municipios_no_encontrados'])[:5]:
                logger.warning(f"     - {muni}")
        
        if transformador.stats['codigos_notaria_duplicados']:
            logger.info(f"  ℹ️ Códigos de notaría duplicados: {len(transformador.stats['codigos_notaria_duplicados'])}")
            logger.info(f"     (Mismo despacho con múltiples titulares históricos)")
        
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    logger.info("=" * 70)
    logger.info("TRANSFORMADOR DE NOTARIOS (2 TABLAS)")
    logger.info("=" * 70)
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("\n🛑 Proceso interrumpido")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()