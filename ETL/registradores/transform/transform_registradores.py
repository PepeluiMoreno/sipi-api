#!/usr/bin/env python3
"""
transform_registradores.py - Usa el mismo sistema de conexión que load_geografia.py
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
    }
    
    @staticmethod
    def limpiar_nombre(nombre: str) -> str:
        """Limpia un nombre para comparación básica"""
        if not nombre:
            return ""
        
        # Asegurar que es string
        if isinstance(nombre, bytes):
            try:
                nombre = nombre.decode('utf-8', errors='ignore')
            except:
                nombre = str(nombre)
        
        # Mayúsculas
        nombre = nombre.upper().strip()
        
        # Quitar acentos básicos
        reemplazos = {
            'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 'Ü': 'U',
            'Ñ': 'N'
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
        """Determina si dos nombres son coincidentes"""
        if not a or not b:
            return False
        
        a_limpio = BuscadorGeografico.limpiar_nombre(a)
        b_limpio = BuscadorGeografico.limpiar_nombre(b)
        
        # 1. Coincidencia exacta
        if a_limpio == b_limpio:
            return True
        
        # 2. Casos especiales conocidos
        if a_limpio in BuscadorGeografico.CASOS_ESPECIALES:
            if BuscadorGeografico.CASOS_ESPECIALES[a_limpio] == b_limpio:
                return True
        
        # 3. Uno contiene al otro
        if a_limpio in b_limpio or b_limpio in a_limpio:
            return True
        
        return False


class CSVTransformer:
    """Transformador de CSV usando el mismo sistema de conexión"""
    
    def __init__(self):
        self.buscador = BuscadorGeografico()
        
        # Cache
        self.cache_provincias = {}      # nombre -> id
        self.cache_municipios = {}      # (nombre_muni, nombre_prov) -> id
        self.lista_provincias = []      # Para búsquedas
        self.lista_municipios = {}      # provincia -> [municipios]
        
        self.stats = {
            'total': 0,
            'ok': 0,
            'error': 0,
            'provincias_no_encontradas': [],
            'municipios_no_encontrados': []
        }
    
    async def cargar_datos_geograficos(self):
        """Carga provincias y municipios de la BD usando db_manager"""
        logger.info("📥 Cargando datos geográficos desde la BD...")
        
        try:
            async with db_manager.session() as session:
                # Importar modelos aquí para evitar import circulares
                from sipi.db.models.geografia import Provincia, Municipio
                
                # Provincias
                result = await session.execute(select(Provincia))
                provincias = result.scalars().all()
                
                for provincia in provincias:
                    nombre = provincia.nombre
                    self.cache_provincias[nombre.upper()] = str(provincia.id)
                    self.lista_provincias.append(nombre)
                
                logger.info(f"  Provincias cargadas: {len(self.cache_provincias)}")
                
                # Municipios por provincia
                result = await session.execute(
                    select(Municipio, Provincia.nombre)
                    .join(Provincia, Municipio.provincia_id == Provincia.id)
                )
                
                for municipio, provincia_nombre in result:
                    provincia = provincia_nombre
                    municipio_nombre = municipio.nombre
                    
                    clave = (municipio_nombre.upper(), provincia.upper())
                    self.cache_municipios[clave] = str(municipio.id)
                    
                    if provincia not in self.lista_municipios:
                        self.lista_municipios[provincia] = []
                    self.lista_municipios[provincia].append(municipio_nombre)
                
                logger.info(f"  Municipios cargados: {len(self.cache_municipios)}")
                
                # Log de ejemplo
                logger.debug("Ejemplo de provincias cargadas:")
                for i, (nombre, id) in enumerate(list(self.cache_provincias.items())[:3]):
                    logger.debug(f"  {nombre} -> {id}")
                    
        except Exception as e:
            logger.error(f"❌ Error cargando datos geográficos: {e}")
            raise
    
    def buscar_provincia(self, nombre_provincia_csv: str) -> Optional[str]:
        """Busca provincia con lógica inteligente"""
        if not nombre_provincia_csv:
            return None
        
        nombre_busqueda = nombre_provincia_csv.upper()
        
        # 1. Buscar exacto
        if nombre_busqueda in self.cache_provincias:
            return self.cache_provincias[nombre_busqueda]
        
        # 2. Buscar con limpieza
        nombre_limpio = self.buscador.limpiar_nombre(nombre_busqueda)
        for provincia_bd, provincia_id in self.cache_provincias.items():
            if self.buscador.limpiar_nombre(provincia_bd) == nombre_limpio:
                return provincia_id
        
        # 3. Buscar coincidencia
        for provincia_bd in self.lista_provincias:
            if self.buscador.es_coincidencia(nombre_busqueda, provincia_bd):
                return self.cache_provincias[provincia_bd.upper()]
        
        # 4. Guardar para reporte
        if nombre_busqueda not in self.stats['provincias_no_encontradas']:
            self.stats['provincias_no_encontradas'].append(nombre_busqueda)
        
        return None
    
    def buscar_municipio(self, nombre_municipio_csv: str, nombre_provincia_csv: str) -> Optional[str]:
        """Busca municipio con lógica inteligente"""
        if not nombre_municipio_csv or not nombre_provincia_csv:
            return None
        
        # Primero buscar la provincia
        provincia_id = self.buscar_provincia(nombre_provincia_csv)
        if not provincia_id:
            return None
        
        # Buscar nombre de provincia en BD
        provincia_nombre_bd = None
        for prov_nombre, prov_id in self.cache_provincias.items():
            if prov_id == provincia_id:
                provincia_nombre_bd = prov_nombre
                break
        
        if not provincia_nombre_bd:
            return None
        
        nombre_muni_busqueda = nombre_municipio_csv.upper()
        nombre_prov_busqueda = provincia_nombre_bd
        
        # 1. Buscar exacto en cache
        clave_exacta = (nombre_muni_busqueda, nombre_prov_busqueda)
        if clave_exacta in self.cache_municipios:
            return self.cache_municipios[clave_exacta]
        
        # 2. Buscar en municipios de esa provincia
        if provincia_nombre_bd in self.lista_municipios:
            municipios_provincia = self.lista_municipios[provincia_nombre_bd]
            
            for municipio_bd in municipios_provincia:
                if self.buscador.es_coincidencia(nombre_muni_busqueda, municipio_bd):
                    clave = (municipio_bd.upper(), nombre_prov_busqueda)
                    return self.cache_municipios.get(clave)
        
        # 3. Buscar en todo el cache
        for (muni_bd, prov_bd), muni_id in self.cache_municipios.items():
            if self.buscador.es_coincidencia(prov_bd, provincia_nombre_bd):
                if self.buscador.es_coincidencia(muni_bd, nombre_muni_busqueda):
                    return muni_id
        
        # 4. Guardar para reporte
        error_key = f"{nombre_muni_busqueda} ({nombre_provincia_csv.upper()})"
        if error_key not in self.stats['municipios_no_encontrados']:
            self.stats['municipios_no_encontrados'].append(error_key)
        
        return None
    
    def leer_csv(self, file_path: str) -> List[Dict]:
        """Lee CSV con manejo robusto de encoding"""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        
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
                    
                    # Buscar IDs geográficos
                    municipio_id = self.buscar_municipio(municipio, provincia)
                    
                    if not municipio_id:
                        self.stats['error'] += 1
                        logger.warning(f"  Fila {idx}: No encontrado '{municipio}' en '{provincia}'")
                        continue
                    
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
                    'municipio_id', 'audit_creado_en', 'audit_creado_por'
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