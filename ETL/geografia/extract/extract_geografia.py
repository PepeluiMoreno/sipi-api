#!/usr/bin/env python3
"""
extract_geografia.py

Extrae datos geográficos del INE.
Descarga el Excel más reciente del INE y lo guarda en la carpeta extract/.
Genera log en extract/geografia_extract.log
"""

import requests
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import logging

# URL base del INE
INE_BASE_URL = "https://www.ine.es/daco/daco42/codmun/diccionario{year:02d}.xlsx"
MAX_RETRO_YEARS = 5


def setup_logging():
    """Configura logging específico para extracción"""
    script_dir = Path(__file__).parent
    log_file = script_dir / 'geografia_extract.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)


logger = setup_logging()


def safe_print(message):
    """Imprime mensajes de forma segura en Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)


def encontrar_url_ine_disponible() -> Tuple[Optional[str], Optional[int]]:
    """Busca la URL del INE más reciente disponible"""
    current_year = datetime.now().year
    safe_print(f"Buscando datos del INE (año actual: {current_year})...")
    logger.info(f"Buscando datos del INE (año actual: {current_year})")
    
    for year_offset in range(MAX_RETRO_YEARS):
        year_to_try = current_year - year_offset
        url = INE_BASE_URL.format(year=year_to_try % 100)
        
        safe_print(f"  Probando {year_to_try}: {url}")
        logger.info(f"Probando año {year_to_try}: {url}")
        
        try:
            response = requests.head(url, timeout=10, allow_redirects=True)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                if any(x in content_type for x in ['excel', 'spreadsheet', 'octet-stream']):
                    safe_print(f"  URL encontrada para {year_to_try}")
                    logger.info(f"URL encontrada para {year_to_try}")
                    return url, year_to_try
            else:
                logger.warning(f"Año {year_to_try}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Año {year_to_try}: Error de conexión - {e}")
            continue
    
    logger.error(f"No se encontraron datos del INE en los últimos {MAX_RETRO_YEARS} años")
    return None, None


def descargar_excel_ine(output_path: Path) -> Tuple[bool, Optional[int]]:
    """Descarga el Excel del INE"""
    url, year = encontrar_url_ine_disponible()
    
    if not url:
        safe_print(f"ERROR: No se encontraron datos del INE en los últimos {MAX_RETRO_YEARS} años")
        return False, None
    
    try:
        logger.info(f"Iniciando descarga desde: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        file_size_mb = len(response.content) / (1024 * 1024)
        safe_print(f"Descarga exitosa: {file_size_mb:.2f} MB (año {year})")
        logger.info(f"Descarga exitosa: {file_size_mb:.2f} MB (año {year})")
        logger.info(f"Archivo guardado: {output_path}")
        
        return True, year
    except requests.exceptions.RequestException as e:
        safe_print(f"Error descargando: {e}")
        logger.error(f"Error descargando: {e}")
        return False, None


def extract_geografia():
    """Función principal de extracción"""
    safe_print("=" * 80)
    safe_print("EXTRACCIÓN DE DATOS GEOGRÁFICOS DEL INE")
    safe_print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("INICIANDO EXTRACCIÓN DE DATOS GEOGRÁFICOS")
    logger.info("=" * 80)
    
    # Configurar rutas - output en la misma carpeta extract/
    script_dir = Path(__file__).parent
    excel_path = script_dir / 'geografia_ine.xlsx'
    
    logger.info(f"Script ejecutado desde: {script_dir}")
    logger.info(f"Archivo de salida: {excel_path}")
    
    # Descargar o usar archivo existente
    if '--force' in sys.argv or not excel_path.exists():
        logger.info("Forzando descarga o archivo no existe")
        success, year = descargar_excel_ine(excel_path)
        if not success:
            logger.error("Falló la descarga del Excel")
            sys.exit(1)
    else:
        file_size = excel_path.stat().st_size / (1024 * 1024)
        safe_print(f"Usando archivo existente: {excel_path}")
        safe_print(f"  Tamaño: {file_size:.2f} MB")
        safe_print("  Usar --force para descargar nuevo archivo")
        logger.info(f"Usando archivo existente: {excel_path}")
        logger.info(f"Tamaño del archivo: {file_size:.2f} MB")
        year = None
    
    # Registrar archivo generado en el log
    if excel_path.exists():
        file_size = excel_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        logger.info("=" * 50)
        logger.info("RESUMEN DE EXTRACCIÓN")
        logger.info("=" * 50)
        logger.info(f"Archivo generado: {excel_path.name}")
        logger.info(f"Ruta completa: {excel_path}")
        logger.info(f"Tamaño: {file_size_mb:.2f} MB ({file_size:,} bytes)")
        logger.info(f"Año de datos: {year if year else 'Desconocido'}")
        logger.info("=" * 50)
    
    safe_print("\n" + "=" * 80)
    safe_print("EXTRACCIÓN COMPLETADA EXITOSAMENTE")
    safe_print("=" * 80)
    
    logger.info("EXTRACCIÓN COMPLETADA EXITOSAMENTE")
    
    return excel_path, year


if __name__ == '__main__':
    extract_geografia()