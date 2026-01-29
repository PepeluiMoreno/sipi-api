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

from sipi_core.db.sessions.async_session import db_manager
from sqlalchemy import select
import asyncio

etl_base = Path(__file__).parent.parent.parent
sys.path.insert(0, str(etl_base))

from common.ine_resolver import INEResolver

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TransformadorNotarios:
    def __init__(self):
        self.ine_resolver = INEResolver()
        self.notarias = {}
        self.titulares = []
        
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
        logger.info("Cargando datos geográficos...")
        try:
            async with db_manager.session() as session:
                await self.ine_resolver.cargar_desde_bd(session)
                stats = self.ine_resolver.get_stats()
                logger.info(f"CCAA: {stats['ccaa_cargadas']}, Provincias: {stats['provincias_cargadas']}, Municipios: {stats['municipios_cargados']}")
        except Exception as e:
            logger.error(f"Error cargando datos geográficos: {e}")
            raise
    
    def resolver_geografia(
        self,
        nombre_municipio: str,
        nombre_provincia: str,
        codigo_ine_municipio: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        
        if codigo_ine_municipio:
            ccaa_uuid, prov_uuid, muni_uuid = self.ine_resolver.resolver_completo(codigo_ine_municipio)
            if muni_uuid:
                self.stats['resoluciones_por_ine'] += 1
                return (ccaa_uuid, prov_uuid, muni_uuid, codigo_ine_municipio)

        ccaa_uuid, prov_uuid, muni_uuid = self.ine_resolver.resolver_por_nombre(
            nombre_municipio,
            nombre_provincia
        )

        if muni_uuid:
            self.stats['resoluciones_por_nombre'] += 1
            codigo_ine = self.ine_resolver.municipio_uuid_to_ine.get(muni_uuid)
            return (ccaa_uuid, prov_uuid, muni_uuid, codigo_ine)

        self.stats['municipios_no_encontrados'].add(
            f"{nombre_municipio.upper()} ({nombre_provincia.upper()})"
        )
        return (None, None, None, None)
    
    def leer_csv(self, file_path: str) -> List[Dict]:
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    sample = f.read(1024)
                    f.seek(0)
                    delimiter = ';' if ';' in sample and sample.count(';') > sample.count(',') else ','
                    reader = csv.DictReader(f, delimiter=delimiter)
                    data = list(reader)
                    logger.info(f"CSV leído: {encoding}, delimitador: '{delimiter}'")
                    return data
            except UnicodeDecodeError:
                continue
            except Exception:
                continue
        
        raise ValueError(f"No se pudo leer el CSV {file_path}")
    
    def extraer_codigo_postal(self, direccion: str) -> Tuple[str, str]:
        if not direccion:
            return "", ""
        
        match = re.search(r'\b(\d{5})\b', direccion)
        if match:
            cp = match.group(1)
            direccion_limpia = direccion.replace(cp, '').strip()
            direccion_limpia = re.sub(r'\s+', ' ', direccion_limpia)
            return direccion_limpia, cp
        
        return direccion, ""
    
    def procesar_csv(self, input_file: str) -> Tuple[List[Dict], List[Dict]]:
        logger.info(f"Procesando: {input_file}")
        data = self.leer_csv(input_file)
        logger.info(f"Filas: {len(data)}")
        
        for idx, fila in enumerate(data, 1):
            self.stats['total_filas'] += 1
            
            try:
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
                
                if not codigo_notaria or not apellidos_nombre or not municipio or not provincia:
                    self.stats['errores'] += 1
                    continue
                
                codigo_ine_csv = fila.get('codigo_ine_municipio', '').strip()

                ccaa_uuid, prov_uuid, municipio_id, codigo_ine_usado = self.resolver_geografia(
                    municipio,
                    provincia,
                    codigo_ine_csv if codigo_ine_csv else None
                )

                if not municipio_id:
                    self.stats['errores'] += 1
                    continue
                
                direccion_limpia, codigo_postal = self.extraer_codigo_postal(direccion_original)
                
                if codigo_notaria not in self.notarias:
                    notaria_id = str(uuid.uuid4())
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
                        'activa': True,
                        'audit_creado_en': datetime.utcnow().isoformat(),
                        'audit_creado_por': 'transform_notarios.py',
                    }

                    self.stats['notarias_creadas'] += 1
                else:
                    self.stats['codigos_notaria_duplicados'].append(codigo_notaria)
                    notaria_id = self.notarias[codigo_notaria]['id']
                
                titular = {
                    'id': str(uuid.uuid4()),
                    'apellidos_nombre': apellidos_nombre,
                    'email_personal': email_personal,
                    'email_corporativo': email_corporativo,
                    'codigo_ultimas_voluntades': codigo_ultimas_voluntades,
                    'idiomas_extranjeros': idiomas_extranjeros,
                    'estado': estado,
                    'notaria_id': notaria_id,
                    'fecha_inicio': datetime.utcnow().date().isoformat(),
                    'fecha_fin': None,
                    'audit_creado_en': datetime.utcnow().isoformat(),
                    'audit_creado_por': 'transform_notarios.py',
                }
                
                self.titulares.append(titular)
                self.stats['titulares_creados'] += 1
                
                if idx % 100 == 0:
                    logger.info(f"Procesadas {idx}/{len(data)} filas")
                
            except Exception as e:
                logger.error(f"Fila {idx}: Error {e}")
                self.stats['errores'] += 1
        
        return list(self.notarias.values()), self.titulares
    
    def guardar_csvs(self, notarias: List[Dict], titulares: List[Dict], 
                     output_dir: str, timestamp: str):
        
        os.makedirs(output_dir, exist_ok=True)
        
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
            
            logger.info(f"Notarias: {notarias_file} ({len(notarias)} registros)")
        
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
            
            logger.info(f"Titulares: {titulares_file} ({len(titulares)} registros)")
    
    def generar_reporte(self, input_file: str, output_dir: str, timestamp: str):
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
        
        logger.info(f"Reporte: {reporte_file}")


def encontrar_csv_mas_reciente(directorio: str, patron: str = "notarios_espana*.csv") -> Optional[str]:
    archivos = glob.glob(os.path.join(directorio, patron))
    
    if not archivos:
        return None
    
    archivos.sort(key=os.path.getmtime, reverse=True)
    return archivos[0]


async def main_async():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    notarios_dir = os.path.dirname(script_dir)
    extract_dir = os.path.join(notarios_dir, 'extract')
    transform_dir = script_dir
    
    csv_path = encontrar_csv_mas_reciente(extract_dir)
    
    if not csv_path:
        logger.error(f"No hay CSVs de notarios en {extract_dir}")
        if os.path.exists(extract_dir):
            archivos = [f for f in os.listdir(extract_dir) if f.endswith('.csv')]
            if archivos:
                logger.info("Archivos CSV encontrados en extract/:")
                for archivo in archivos:
                    logger.info(f"  - {archivo}")
        return
    
    logger.info(f"CSV encontrado: {csv_path}")
    
    transformador = TransformadorNotarios()
    
    try:
        await transformador.cargar_datos_geograficos()
        notarias, titulares = transformador.procesar_csv(csv_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        transformador.guardar_csvs(notarias, titulares, transform_dir, timestamp)
        transformador.generar_reporte(csv_path, transform_dir, timestamp)
        
        logger.info("=" * 70)
        logger.info("TRANSFORMACIÓN COMPLETADA")
        logger.info("=" * 70)
        logger.info(f"Total filas CSV: {transformador.stats['total_filas']}")
        logger.info(f"Notarías creadas: {transformador.stats['notarias_creadas']}")
        logger.info(f"Titulares creados: {transformador.stats['titulares_creados']}")
        logger.info(f"Resoluciones por INE: {transformador.stats['resoluciones_por_ine']}")
        logger.info(f"Resoluciones por nombre: {transformador.stats['resoluciones_por_nombre']}")
        logger.info(f"Errores: {transformador.stats['errores']}")
        
        if transformador.stats['municipios_no_encontrados']:
            logger.warning(f"Municipios no encontrados: {len(transformador.stats['municipios_no_encontrados'])}")
            for muni in list(transformador.stats['municipios_no_encontrados'])[:5]:
                logger.warning(f"  - {muni}")
        
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()


def main():
    logger.info("=" * 70)
    logger.info("TRANSFORMADOR DE NOTARIOS (2 TABLAS)")
    logger.info("=" * 70)
    
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Proceso interrumpido")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()