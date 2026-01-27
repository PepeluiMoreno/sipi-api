# transform_notarios.py
"""
Transforma CSV de notarios a dos tablas: notarias y notarias_titulares
Usa el mismo sistema de conexión que load_geografia.py
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
from collections import defaultdict

# Importar el mismo sistema de conexión
from sipi.db.sessions.async_session import db_manager
from sqlalchemy import select
import asyncio

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BuscadorGeografico:
    """Búsqueda inteligente de nombres geográficos"""
    
    CASOS_ESPECIALES = {
        'ALAVA': 'ARABA',
        'ARABA': 'ALAVA',
        'GUIPUZCOA': 'GIPUZKOA', 
        'GIPUZKOA': 'GUIPUZCOA',
        'VIZCAYA': 'BIZKAIA',
        'BIZKAIA': 'VIZCAYA',
        'ORENSE': 'OURENSE',
        'OURENSE': 'ORENSE',
        'GERONA': 'GIRONA',
        'GIRONA': 'GERONA',
        'LERIDA': 'LLEIDA',
        'LLEIDA': 'LERIDA',
        'LA CORUÑA': 'A CORUÑA',
        'A CORUÑA': 'LA CORUÑA',
    }
    
    @staticmethod
    def limpiar_nombre(nombre: str) -> str:
        """Limpia un nombre para comparación básica"""
        if not nombre:
            return ""
        
        nombre = str(nombre).upper().strip()
        
        # Quitar acentos
        reemplazos = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ü': 'U', 'Ñ': 'N'
        }
        for old, new in reemplazos.items():
            nombre = nombre.replace(old, new)
        
        # Quitar puntuación
        nombre = re.sub(r'[^\w\s]', ' ', nombre)
        
        # Normalizar espacios
        nombre = re.sub(r'\s+', ' ', nombre).strip()
        
        return nombre
    
    @staticmethod
    def es_coincidencia(a: str, b: str) -> bool:
        """Determina si dos nombres coinciden"""
        if not a or not b:
            return False
        
        a_limpio = BuscadorGeografico.limpiar_nombre(a)
        b_limpio = BuscadorGeografico.limpiar_nombre(b)
        
        # 1. Coincidencia exacta
        if a_limpio == b_limpio:
            return True
        
        # 2. Casos especiales
        if a_limpio in BuscadorGeografico.CASOS_ESPECIALES:
            if BuscadorGeografico.CASOS_ESPECIALES[a_limpio] == b_limpio:
                return True
        
        # 3. Uno contiene al otro (para casos como "La Coruña" vs "Coruña")
        if a_limpio in b_limpio or b_limpio in a_limpio:
            return True
        
        return False


class TransformadorNotarios:
    """Transforma CSV de notarios a dos tablas relacionadas"""
    
    def __init__(self):
        self.buscador = BuscadorGeografico()
        
        # Cache geográfico
        self.cache_provincias = {}
        self.cache_municipios = {}
        self.lista_provincias = []
        self.lista_municipios = {}
        
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
            'codigos_notaria_duplicados': []
        }
    
    async def cargar_datos_geograficos(self):
        """Carga provincias y municipios de la BD"""
        logger.info("📥 Cargando datos geográficos...")
        
        try:
            async with db_manager.session() as session:
                from sipi.db.models.geografia import Provincia, Municipio
                
                # Provincias
                result = await session.execute(select(Provincia))
                provincias = result.scalars().all()
                
                for provincia in provincias:
                    nombre = provincia.nombre
                    self.cache_provincias[nombre.upper()] = str(provincia.id)
                    self.lista_provincias.append(nombre)
                
                logger.info(f"  ✅ {len(self.cache_provincias)} provincias cargadas")
                
                # Municipios
                result = await session.execute(
                    select(Municipio, Provincia.nombre)
                    .join(Provincia, Municipio.provincia_id == Provincia.id)
                )
                
                for municipio, provincia_nombre in result:
                    clave = (municipio.nombre.upper(), provincia_nombre.upper())
                    self.cache_municipios[clave] = str(municipio.id)
                    
                    if provincia_nombre not in self.lista_municipios:
                        self.lista_municipios[provincia_nombre] = []
                    self.lista_municipios[provincia_nombre].append(municipio.nombre)
                
                logger.info(f"  ✅ {len(self.cache_municipios)} municipios cargados")
                
        except Exception as e:
            logger.error(f"❌ Error cargando datos geográficos: {e}")
            raise
    
    def buscar_provincia(self, nombre_provincia: str) -> Optional[str]:
        """Busca provincia con lógica inteligente"""
        if not nombre_provincia:
            return None
        
        nombre_busqueda = nombre_provincia.upper()
        
        # 1. Búsqueda exacta
        if nombre_busqueda in self.cache_provincias:
            return self.cache_provincias[nombre_busqueda]
        
        # 2. Búsqueda con limpieza
        nombre_limpio = self.buscador.limpiar_nombre(nombre_busqueda)
        for provincia_bd, provincia_id in self.cache_provincias.items():
            if self.buscador.limpiar_nombre(provincia_bd) == nombre_limpio:
                return provincia_id
        
        # 3. Búsqueda por coincidencia
        for provincia_bd in self.lista_provincias:
            if self.buscador.es_coincidencia(nombre_busqueda, provincia_bd):
                return self.cache_provincias[provincia_bd.upper()]
        
        # No encontrado
        self.stats['provincias_no_encontradas'].add(nombre_busqueda)
        return None
    
    def buscar_municipio(self, nombre_municipio: str, nombre_provincia: str) -> Optional[str]:
        """Busca municipio con lógica inteligente"""
        if not nombre_municipio or not nombre_provincia:
            return None
        
        # Buscar provincia primero
        provincia_id = self.buscar_provincia(nombre_provincia)
        if not provincia_id:
            return None
        
        # Encontrar nombre de provincia en BD
        provincia_nombre_bd = None
        for prov_nombre, prov_id in self.cache_provincias.items():
            if prov_id == provincia_id:
                provincia_nombre_bd = prov_nombre
                break
        
        if not provincia_nombre_bd:
            return None
        
        nombre_muni_busqueda = nombre_municipio.upper()
        
        # 1. Búsqueda exacta
        clave_exacta = (nombre_muni_busqueda, provincia_nombre_bd)
        if clave_exacta in self.cache_municipios:
            return self.cache_municipios[clave_exacta]
        
        # 2. Búsqueda en municipios de esa provincia
        if provincia_nombre_bd in self.lista_municipios:
            for municipio_bd in self.lista_municipios[provincia_nombre_bd]:
                if self.buscador.es_coincidencia(nombre_muni_busqueda, municipio_bd):
                    clave = (municipio_bd.upper(), provincia_nombre_bd)
                    return self.cache_municipios.get(clave)
        
        # 3. Búsqueda en todo el cache
        for (muni_bd, prov_bd), muni_id in self.cache_municipios.items():
            if self.buscador.es_coincidencia(prov_bd, provincia_nombre_bd):
                if self.buscador.es_coincidencia(muni_bd, nombre_muni_busqueda):
                    return muni_id
        
        # No encontrado
        self.stats['municipios_no_encontrados'].add(f"{nombre_muni_busqueda} ({nombre_provincia.upper()})")
        return None
    
    def leer_csv(self, file_path: str) -> List[Dict]:
        """Lee CSV con manejo robusto de encoding"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
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
                
                # Resolver municipio
                municipio_id = self.buscar_municipio(municipio, provincia)
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
                    
                    self.notarias[codigo_notaria] = {
                        'id': notaria_id,
                        'codigo_notaria': codigo_notaria,
                        'direccion': direccion_limpia,
                        'codigo_postal': codigo_postal,
                        'telefono': telefono,
                        'fax': fax,
                        'email': email_notaria,
                        'municipio_id': municipio_id,
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
                'telefono', 'fax', 'email', 'municipio_id', 'activa',
                'audit_creado_en', 'audit_creado_por'
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
    extract_dir = os.path.join(script_dir, '../extract')
    transform_dir = os.path.join(script_dir, '../transform')
    
    # Buscar CSV
    csv_path = encontrar_csv_mas_reciente(extract_dir)
    if not csv_path:
        logger.error(f"❌ No hay CSVs de notarios en {extract_dir}")
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