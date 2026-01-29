#!/usr/bin/env python3
"""
TRANSFORMACIÓN GEOGRÁFICA - ETAPA DE TRANSFORMACIÓN

ENTRADA:
  - Archivo: ../extract/geografia_ine.xlsx
    Contenido: Datos geográficos del INE descargados por extract_geografia.py
    Formato: Excel con columnas CODAUTO, CPRO, CMUN, DC, NOMBRE

SALIDA (en carpeta transform/):
  - comunidades_autonomas.csv
    Columnas: codigo_ine, nombre_oficial, nombre_alternativo, nombre_cooficial, activo
    Entregable a: Proceso de carga a base de datos
  
  - provincias.csv
    Columnas: codigo_ine, nombre_oficial, nombre_alternativo, nombre_cooficial, 
              comunidad_autonoma_codigo, activo
    Entregable a: Proceso de carga a base de datos
  
  - municipios.csv
    Columnas: comunidad_autonoma_codigo, codigo_ine, codigo_ine_completo,
              nombre_oficial, nombre_alternativo, nombre_cooficial,
              provincia_codigo, activo
    Entregable a: Proceso de carga a base de datos y georeferenciación

Log: transform/geografia_transform.log
Usa constantes de: common/ine_constants.py
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Optional, Tuple
import logging

# --- Importaciones ---
# Añadir el directorio parent al path para poder importar desde common/
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent  # ETL/
common_dir = project_root / 'common'  # ETL/common/

sys.path.insert(0, str(project_root))

from common.ine_constants import (
    CCAA_NOMBRE_OFICIAL,
    CCAA_NOMBRE_ALTERNATIVO,
    CCAA_NOMBRE_COOFICIAL,
    PROVINCIA_A_CCAA,
    NOMBRES_PROVINCIAS
)

# Configurar logging
def setup_logging(log_file_name: str):
    """Configura logging básico"""
    log_file = current_dir / log_file_name
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    return logging.getLogger(__name__)

def safe_print(message):
    """Imprime mensajes de forma segura"""
    try:
        print(message)
    except UnicodeEncodeError:
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)


# ========== FUNCIONES DE TRANSFORMACIÓN ==========

def detectar_cabecera_excel(excel_path: Path) -> int:
    """Detecta automáticamente la fila de cabeceras en el Excel del INE"""
    df_prueba = pd.read_excel(excel_path, header=None, nrows=15)
    
    patrones_cabecera = ['CODAUTO', 'CPRO', 'CMUN', 'DC', 'NOMBRE']
    
    for i in range(len(df_prueba)):
        fila_str = ' '.join(str(cell).upper() for cell in df_prueba.iloc[i].fillna('').tolist())
        
        if any(patron in fila_str for patron in patrones_cabecera):
            return i
    
    return 0


def procesar_nombre_provincia(codigo_provincia: str) -> Tuple[str, str, str]:
    """
    Procesa el nombre de provincia y determina nombre_oficial, nombre_alternativo, nombre_cooficial.
    """
    nombre_oficial = NOMBRES_PROVINCIAS.get(codigo_provincia, f'Provincia {codigo_provincia}')
    
    if '/' in nombre_oficial:
        partes = nombre_oficial.split('/')
        if len(partes) == 2:
            # Para provincias con nombres bilingües
            nombre_cooficial = partes[0].strip()  # Ej: "Araba" (euskera)
            nombre_alternativo = partes[1].strip()  # Ej: "Álava" (español)
            return nombre_oficial, nombre_alternativo, nombre_cooficial
    
    # Sin separador - los tres nombres iguales
    return nombre_oficial, nombre_oficial, nombre_oficial


def procesar_nombre_municipio(nombre_ine: str, codigo_provincia: str = None) -> Tuple[str, str, str]:
    """
    Procesa el nombre del municipio del INE y determina nombre_oficial, nombre_alternativo, nombre_cooficial.
    """
    if not isinstance(nombre_ine, str):
        nombre_ine = str(nombre_ine)
    
    nombre_ine = nombre_ine.strip()
    nombre_oficial = nombre_ine
    
    for separador in ['/', '-']:
        if separador in nombre_ine:
            partes = nombre_ine.split(separador)
            if len(partes) == 2:
                nombre_alternativo = partes[0].strip()
                nombre_cooficial = partes[1].strip()
                return nombre_oficial, nombre_alternativo, nombre_cooficial
    
    # Sin separador - los tres nombres iguales
    return nombre_oficial, nombre_oficial, nombre_oficial


def transformar_excel_ine(excel_path: Path, year: Optional[int] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    TRANSFORMACIÓN PRINCIPAL
    
    Convierte Excel del INE en 3 DataFrames estructurados:
    1. Comunidades Autónomas (19 registros)
    2. Provincias (52 registros)  
    3. Municipios (~8,132 registros)
    """
    safe_print(f"Transformando Excel del INE...")
    logger.info(f"Transformando Excel del INE")
    logger.info(f"Leyendo archivo: {excel_path}")
    
    # Detectar cabecera automáticamente
    fila_cabecera = detectar_cabecera_excel(excel_path)
    
    # Leer Excel con cabecera correcta
    df = pd.read_excel(excel_path, header=fila_cabecera)
    
    # Limpiar datos
    df = df.dropna(how='all')
    df = df.reset_index(drop=True)
    
    safe_print(f"Registros cargados: {len(df):,}")
    
    # Detección de columnas
    col_mapping = {}
    for col in df.columns:
        col_str = str(col).upper()
        if 'CODAUTO' in col_str or 'CCAA' in col_str:
            col_mapping['ccaa'] = col
        elif 'CPRO' in col_str or 'PROV' in col_str:
            col_mapping['provincia'] = col
        elif 'CMUN' in col_str or 'MUNI' in col_str:
            col_mapping['municipio'] = col
        elif 'DC' in col_str or 'DIGITO' in col_str or 'CONTROL' in col_str:
            col_mapping['digito_control'] = col
        elif 'NOMBRE' in col_str or 'LITERAL' in col_str:
            col_mapping['nombre'] = col
    
    # Si no detectamos todas las columnas, asumir nombres estándar
    if len(col_mapping) < 5:
        logger.warning(f"No se detectaron todas las columnas automáticamente. Mapeo: {col_mapping}")
        
        columns = list(df.columns)
        if len(columns) >= 5:
            col_mapping['ccaa'] = columns[0]
            col_mapping['provincia'] = columns[1]
            col_mapping['municipio'] = columns[2]
            col_mapping['digito_control'] = columns[3]
            col_mapping['nombre'] = columns[4]
    
    logger.info(f"Columnas mapeadas: {col_mapping}")
    
    # Verificar columnas mínimas
    columnas_requeridas = ['provincia', 'municipio', 'nombre']
    for col in columnas_requeridas:
        if col not in col_mapping:
            safe_print(f"ERROR: No se encontró la columna '{col}' en el Excel")
            logger.error(f"No se encontró la columna '{col}' en el Excel")
            sys.exit(1)
    
    # Limpiar y formatear datos
    df[col_mapping['provincia']] = df[col_mapping['provincia']].astype(str).str.zfill(2)
    df[col_mapping['municipio']] = df[col_mapping['municipio']].astype(str).str.zfill(3)
    
    # Generar código INE de 5 dígitos
    df['codigo_ine_5'] = df[col_mapping['provincia']] + df[col_mapping['municipio']]
    
    # Generar código INE completo de 7 dígitos
    if 'digito_control' in col_mapping:
        df['digito_control'] = df[col_mapping['digito_control']].astype(str).str.zfill(2)
        df['codigo_ine_7'] = df['codigo_ine_5'] + df['digito_control']
    else:
        safe_print("ADVERTENCIA: No se encontró columna de dígito de control")
        logger.warning("No se encontró columna de dígito de control en el Excel")
        df['codigo_ine_7'] = df['codigo_ine_5'] + '00'
    
    # 1. DataFrame de CCAA
    ccaa_data = []
    for codigo_ccaa in CCAA_NOMBRE_OFICIAL.keys():
        ccaa_data.append({
            'codigo_ine': codigo_ccaa,
            'nombre_oficial': CCAA_NOMBRE_OFICIAL.get(codigo_ccaa, ''),
            'nombre_alternativo': CCAA_NOMBRE_ALTERNATIVO.get(codigo_ccaa, ''),
            'nombre_cooficial': CCAA_NOMBRE_COOFICIAL.get(codigo_ccaa, ''),
            'activo': True
        })
    
    df_ccaa = pd.DataFrame(ccaa_data)
    
    # 2. DataFrame de Provincias
    provincias_data = []
    for codigo_prov in sorted(df[col_mapping['provincia']].unique()):
        nombre_oficial, nombre_alternativo, nombre_cooficial = procesar_nombre_provincia(codigo_prov)
        
        provincias_data.append({
            'codigo_ine': codigo_prov,
            'nombre_oficial': nombre_oficial,
            'nombre_alternativo': nombre_alternativo,
            'nombre_cooficial': nombre_cooficial,
            'comunidad_autonoma_codigo': PROVINCIA_A_CCAA.get(codigo_prov, '00'),
            'activo': True
        })
    
    df_provincias = pd.DataFrame(provincias_data)
    
    # 3. DataFrame de Municipios
    municipios_data = []
    for _, row in df.iterrows():
        codigo_provincia = row[col_mapping['provincia']]
        nombre_ine = str(row[col_mapping['nombre']]).strip()
        
        nombre_oficial, nombre_alternativo, nombre_cooficial = procesar_nombre_municipio(
            nombre_ine, codigo_provincia
        )
        
        comunidad_autonoma_codigo = PROVINCIA_A_CCAA.get(codigo_provincia, '00')
        
        municipios_data.append({
            'comunidad_autonoma_codigo': comunidad_autonoma_codigo,
            'codigo_ine': row['codigo_ine_5'],
            'codigo_ine_completo': row['codigo_ine_7'],
            'nombre_oficial': nombre_oficial,
            'nombre_alternativo': nombre_alternativo,
            'nombre_cooficial': nombre_cooficial,
            'provincia_codigo': codigo_provincia,
            'activo': True
        })
    
    df_municipios = pd.DataFrame(municipios_data)
    
    # Estadísticas
    safe_print(f"{len(df_ccaa)} CCAA, {len(df_provincias)} provincias, "
               f"{len(df_municipios):,} municipios generados")
    
    logger.info(f"DataFrames generados:")
    logger.info(f"  - CCAA: {len(df_ccaa)} registros")
    logger.info(f"  - Provincias: {len(df_provincias)} registros")
    logger.info(f"  - Municipios: {len(df_municipios):,} registros")
    
    return df_ccaa, df_provincias, df_municipios


def guardar_csvs(df_ccaa: pd.DataFrame, df_provincias: pd.DataFrame, 
                 df_municipios: pd.DataFrame, output_dir: Path) -> Tuple[Path, Path, Path]:
    """
    GUARDADO DE ARCHIVOS CSV
    
    Guarda los 3 DataFrames como archivos CSV en la carpeta transform/
    Retorna las rutas de los archivos generados.
    """
    # Guardar CSV de Comunidades Autónomas
    ccaa_path = output_dir / 'comunidades_autonomas.csv'
    df_ccaa_sorted = df_ccaa[['codigo_ine', 'nombre_oficial', 'nombre_alternativo', 
                              'nombre_cooficial', 'activo']]
    df_ccaa_sorted.to_csv(ccaa_path, index=False, encoding='utf-8-sig')
    ccaa_size = ccaa_path.stat().st_size
    safe_print(f"  ✓ {ccaa_path.name}: {len(df_ccaa)} registros ({ccaa_size:,} bytes)")
    logger.info(f"Archivo generado: {ccaa_path.name} ({ccaa_size:,} bytes)")
    
    # Guardar CSV de Provincias
    prov_path = output_dir / 'provincias.csv'
    df_provincias_sorted = df_provincias[['codigo_ine', 'nombre_oficial', 'nombre_alternativo', 
                                         'nombre_cooficial', 'comunidad_autonoma_codigo', 'activo']]
    df_provincias_sorted.to_csv(prov_path, index=False, encoding='utf-8-sig')
    prov_size = prov_path.stat().st_size
    safe_print(f"  ✓ {prov_path.name}: {len(df_provincias)} registros ({prov_size:,} bytes)")
    logger.info(f"Archivo generado: {prov_path.name} ({prov_size:,} bytes)")
    
    # Guardar CSV de Municipios
    muni_path = output_dir / 'municipios.csv'
    df_municipios_sorted = df_municipios[['comunidad_autonoma_codigo',
                                         'codigo_ine',
                                         'codigo_ine_completo',
                                         'nombre_oficial',
                                         'nombre_alternativo',
                                         'nombre_cooficial',
                                         'provincia_codigo',
                                         'activo']]
    df_municipios_sorted.to_csv(muni_path, index=False, encoding='utf-8-sig')
    muni_size = muni_path.stat().st_size
    safe_print(f"  ✓ {muni_path.name}: {len(df_municipios):,} registros ({muni_size:,} bytes)")
    logger.info(f"Archivo generado: {muni_path.name} ({muni_size:,} bytes)")
    
    return ccaa_path, prov_path, muni_path


def transformar_geografia():
    """
    FUNCIÓN PRINCIPAL DE TRANSFORMACIÓN
    
    Orquesta todo el proceso:
    1. Lee archivo de entrada desde extract/
    2. Transforma datos
    3. Guarda CSVs en transform/
    4. Reporta resultados
    """
    safe_print("=" * 80)
    safe_print("TRANSFORMACIÓN DE DATOS GEOGRÁFICOS DEL INE")
    safe_print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("INICIANDO TRANSFORMACIÓN DE DATOS GEOGRÁFICOS")
    logger.info("=" * 80)
    
    # Configurar rutas
    script_dir = Path(__file__).parent
    extract_dir = script_dir.parent / 'extract'
    excel_path = extract_dir / 'geografia_ine.xlsx'
    
    logger.info(f"Script ejecutado desde: {script_dir}")
    logger.info(f"Buscando archivo de entrada: {excel_path}")
    
    # Verificar archivo de entrada
    if not excel_path.exists():
        safe_print(f"ERROR: No se encuentra el archivo Excel: {excel_path}")
        logger.error(f"No se encuentra el archivo Excel: {excel_path}")
        logger.error("Ejecuta primero extract_geografia.py desde la carpeta extract/")
        sys.exit(1)
    
    input_size = excel_path.stat().st_size / (1024 * 1024)  # MB
    safe_print(f"Archivo de entrada encontrado: {excel_path.name}")
    safe_print(f"Tamaño: {input_size:.2f} MB")
    logger.info(f"Tamaño del archivo de entrada: {input_size:.2f} MB")
    
    # Transformar Excel
    try:
        df_ccaa, df_provincias, df_municipios = transformar_excel_ine(excel_path)
    except Exception as e:
        safe_print(f"ERROR transformando Excel: {e}")
        logger.error(f"Error transformando Excel: {e}", exc_info=True)
        sys.exit(1)
    
    # Guardar CSV
    safe_print(f"\nGuardando CSVs en {script_dir}:")
    logger.info(f"Guardando archivos CSV en: {script_dir}")
    
    try:
        ccaa_path, prov_path, muni_path = guardar_csvs(df_ccaa, df_provincias, df_municipios, script_dir)
    except Exception as e:
        safe_print(f"ERROR guardando CSV: {e}")
        logger.error(f"Error guardando CSV: {e}", exc_info=True)
        sys.exit(1)
    
    # Resumen final
    logger.info("=" * 50)
    logger.info("RESUMEN DE TRANSFORMACIÓN")
    logger.info("=" * 50)
    logger.info(f"Archivo de entrada: {excel_path.name} ({input_size:.2f} MB)")
    logger.info("Archivos generados:")
    logger.info(f"  1. {ccaa_path.name}: {len(df_ccaa)} registros")
    logger.info(f"  2. {prov_path.name}: {len(df_provincias)} registros")
    logger.info(f"  3. {muni_path.name}: {len(df_municipios):,} registros")
    logger.info(f"Total registros transformados: {len(df_ccaa) + len(df_provincias) + len(df_municipios):,}")
    logger.info("=" * 50)
    
    safe_print("\n" + "=" * 80)
    safe_print("TRANSFORMACIÓN COMPLETADA EXITOSAMENTE")
    safe_print("=" * 80)
    
    logger.info("TRANSFORMACIÓN COMPLETADA EXITOSAMENTE")
    
    return df_ccaa, df_provincias, df_municipios


if __name__ == '__main__':
    logger = setup_logging('geografia_transform.log')
    transformar_geografia()