#!/usr/bin/env python3
"""
transform_geografia.py

Transforma datos geográficos del INE.
Lee el Excel de ../extract/ y genera CSV en la carpeta transform/.
Genera log en transform/geografia_transform.log
"""

import pandas as pd
import sys
from pathlib import Path
from typing import Optional
import logging

# Diccionarios de mapeo
CCAA_OFICIAL = {
    '01': 'Andalucía', '02': 'Aragón', '03': 'Asturias, Principado de',
    '04': 'Balears, Illes', '05': 'Canarias', '06': 'Cantabria',
    '07': 'Castilla y León', '08': 'Castilla-La Mancha', '09': 'Cataluña',
    '10': 'Comunitat Valenciana', '11': 'Extremadura', '12': 'Galicia',
    '13': 'Madrid, Comunidad de', '14': 'Murcia, Región de',
    '15': 'Navarra, Comunidad Foral de', '16': 'País Vasco',
    '17': 'Rioja, La', '18': 'Ceuta', '19': 'Melilla',
}

PROVINCIA_A_CCAA = {
    '04': '01', '11': '01', '14': '01', '18': '01', '21': '01', '23': '01', '29': '01', '41': '01',
    '22': '02', '44': '02', '50': '02', '33': '03', '07': '04', '35': '05', '38': '05',
    '39': '06', '05': '07', '09': '07', '24': '07', '34': '07', '37': '07', '40': '07',
    '42': '07', '47': '07', '49': '07', '02': '08', '13': '08', '16': '08', '19': '08',
    '45': '08', '08': '09', '17': '09', '25': '09', '43': '09', '03': '10', '12': '10',
    '46': '10', '06': '11', '10': '11', '15': '12', '27': '12', '32': '12', '36': '12',
    '28': '13', '30': '14', '31': '15', '01': '16', '20': '16', '48': '16', '26': '17',
    '51': '18', '52': '19',
}

NOMBRES_PROVINCIAS = {
    '01': 'Araba/Álava', '02': 'Albacete', '03': 'Alicante/Alacant', '04': 'Almería',
    '05': 'Ávila', '06': 'Badajoz', '07': 'Balears, Illes', '08': 'Barcelona',
    '09': 'Burgos', '10': 'Cáceres', '11': 'Cádiz', '12': 'Castellón/Castelló',
    '13': 'Ciudad Real', '14': 'Córdoba', '15': 'Coruña, A', '16': 'Cuenca',
    '17': 'Girona', '18': 'Granada', '19': 'Guadalajara', '20': 'Gipuzkoa',
    '21': 'Huelva', '22': 'Huesca', '23': 'Jaén', '24': 'León', '25': 'Lleida',
    '26': 'Rioja, La', '27': 'Lugo', '28': 'Madrid', '29': 'Málaga', '30': 'Murcia',
    '31': 'Navarra', '32': 'Ourense', '33': 'Asturias', '34': 'Palencia',
    '35': 'Palmas, Las', '36': 'Pontevedra', '37': 'Salamanca',
    '38': 'Santa Cruz de Tenerife', '39': 'Cantabria', '40': 'Segovia',
    '41': 'Sevilla', '42': 'Soria', '43': 'Tarragona', '44': 'Teruel',
    '45': 'Toledo', '46': 'Valencia/València', '47': 'Valladolid', '48': 'Bizkaia',
    '49': 'Zamora', '50': 'Zaragoza', '51': 'Ceuta', '52': 'Melilla',
}


def setup_logging():
    """Configura logging específico para transformación"""
    script_dir = Path(__file__).parent
    log_file = script_dir / 'geografia_transform.log'
    
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


def transformar_excel_ine(excel_path: Path, year: Optional[int] = None) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Transforma el Excel del INE en DataFrames estructurados"""
    safe_print(f"Transformando Excel del INE{' ' + str(year) if year else ''}...")
    logger.info(f"Transformando Excel del INE{' ' + str(year) if year else ''}")
    logger.info(f"Leyendo archivo: {excel_path}")
    
    df = pd.read_excel(excel_path, header=1)
    safe_print(f"Registros cargados: {len(df):,}")
    logger.info(f"Registros cargados del Excel: {len(df):,}")
    
    # Detección de columnas
    col_mapping = {}
    for col in df.columns:
        col_upper = str(col).upper()
        if 'CPRO' in col_upper or 'PROV' in col_upper:
            col_mapping['provincia'] = col
        elif 'CMUN' in col_upper or 'MUNI' in col_upper:
            col_mapping['municipio'] = col
        elif 'NOMBRE' in col_upper or 'LITERAL' in col_upper:
            col_mapping['nombre'] = col
    
    logger.info(f"Columnas detectadas: {col_mapping}")
    
    # Si no encontramos las columnas, usar las primeras 3
    if len(col_mapping) < 3:
        columns = list(df.columns)
        col_mapping['provincia'] = columns[0] if len(columns) > 0 else 'CPRO'
        col_mapping['municipio'] = columns[1] if len(columns) > 1 else 'CMUN'
        col_mapping['nombre'] = columns[2] if len(columns) > 2 else 'NOMBRE'
        logger.warning(f"Columnas no detectadas automáticamente. Usando: {col_mapping}")
    
    # Limpiar y formatear
    df[col_mapping['provincia']] = df[col_mapping['provincia']].astype(str).str.zfill(2)
    df[col_mapping['municipio']] = df[col_mapping['municipio']].astype(str).str.zfill(3)
    df['codigo_completo'] = df[col_mapping['provincia']] + df[col_mapping['municipio']]
    
    # Generar DataFrames
    df_ccaa = pd.DataFrame([
        {'codigo_ine': k, 'nombre': v, 'nombre_oficial': v, 'activo': True}
        for k, v in CCAA_OFICIAL.items()
    ])
    
    df_provincias = pd.DataFrame([
        {
            'codigo_ine': codigo,
            'nombre': NOMBRES_PROVINCIAS.get(codigo, f'Provincia {codigo}'),
            'nombre_oficial': NOMBRES_PROVINCIAS.get(codigo, f'Provincia {codigo}'),
            'comunidad_autonoma_codigo': PROVINCIA_A_CCAA.get(codigo, '00'),
            'activo': True
        }
        for codigo in df[col_mapping['provincia']].unique()
    ])
    
    df_municipios = pd.DataFrame([
        {
            'codigo_ine': row['codigo_completo'],
            'nombre': str(row[col_mapping['nombre']]).strip(),
            'nombre_oficial': str(row[col_mapping['nombre']]).strip(),
            'provincia_codigo': row[col_mapping['provincia']],
            'activo': True
        }
        for _, row in df.iterrows()
    ])
    
    safe_print(f"{len(df_ccaa)} CCAA, {len(df_provincias)} provincias, "
               f"{len(df_municipios):,} municipios generados")
    
    logger.info(f"DataFrames generados:")
    logger.info(f"  - CCAA: {len(df_ccaa)} registros")
    logger.info(f"  - Provincias: {len(df_provincias)} registros")
    logger.info(f"  - Municipios: {len(df_municipios):,} registros")
    
    return df_ccaa, df_provincias, df_municipios


def guardar_csvs(df_ccaa: pd.DataFrame, df_provincias: pd.DataFrame, 
                 df_municipios: pd.DataFrame, output_dir: Path):
    """Guarda los DataFrames transformados en archivos CSV en la carpeta transform/"""
    
    # Guardar CSV de Comunidades Autónomas
    ccaa_path = output_dir / 'comunidades_autonomas.csv'
    df_ccaa.to_csv(ccaa_path, index=False, encoding='utf-8')
    ccaa_size = ccaa_path.stat().st_size
    safe_print(f"  - {ccaa_path.name}: {len(df_ccaa)} registros")
    logger.info(f"Archivo generado: {ccaa_path.name}")
    logger.info(f"  Ruta: {ccaa_path}")
    logger.info(f"  Registros: {len(df_ccaa)}")
    logger.info(f"  Tamaño: {ccaa_size:,} bytes")
    
    # Guardar CSV de Provincias
    prov_path = output_dir / 'provincias.csv'
    df_provincias.to_csv(prov_path, index=False, encoding='utf-8')
    prov_size = prov_path.stat().st_size
    safe_print(f"  - {prov_path.name}: {len(df_provincias)} registros")
    logger.info(f"Archivo generado: {prov_path.name}")
    logger.info(f"  Ruta: {prov_path}")
    logger.info(f"  Registros: {len(df_provincias)}")
    logger.info(f"  Tamaño: {prov_size:,} bytes")
    
    # Guardar CSV de Municipios
    muni_path = output_dir / 'municipios.csv'
    df_municipios.to_csv(muni_path, index=False, encoding='utf-8')
    muni_size = muni_path.stat().st_size
    safe_print(f"  - {muni_path.name}: {len(df_municipios):,} registros")
    logger.info(f"Archivo generado: {muni_path.name}")
    logger.info(f"  Ruta: {muni_path}")
    logger.info(f"  Registros: {len(df_municipios):,}")
    logger.info(f"  Tamaño: {muni_size:,} bytes")


def transformar_geografia():
    """Función principal de transformación"""
    safe_print("=" * 80)
    safe_print("TRANSFORMACIÓN DE DATOS GEOGRÁFICOS DEL INE")
    safe_print("=" * 80)
    
    logger.info("=" * 80)
    logger.info("INICIANDO TRANSFORMACIÓN DE DATOS GEOGRÁFICOS")
    logger.info("=" * 80)
    
    # Configurar rutas - input desde extract/, output en transform/
    script_dir = Path(__file__).parent
    extract_dir = script_dir.parent / 'extract'
    excel_path = extract_dir / 'geografia_ine.xlsx'
    
    logger.info(f"Script ejecutado desde: {script_dir}")
    logger.info(f"Buscando archivo de entrada: {excel_path}")
    
    if not excel_path.exists():
        safe_print(f"ERROR: No se encuentra el archivo Excel: {excel_path}")
        logger.error(f"No se encuentra el archivo Excel: {excel_path}")
        logger.error("Ejecuta primero extract_geografia.py desde la carpeta extract/")
        sys.exit(1)
    
    # Verificar tamaño del archivo de entrada
    input_size = excel_path.stat().st_size
    logger.info(f"Archivo de entrada encontrado: {excel_path.name}")
    logger.info(f"Tamaño del archivo de entrada: {input_size:,} bytes")
    
    # Transformar Excel
    try:
        df_ccaa, df_provincias, df_municipios = transformar_excel_ine(excel_path)
    except Exception as e:
        safe_print(f"ERROR transformando Excel: {e}")
        logger.error(f"Error transformando Excel: {e}", exc_info=True)
        sys.exit(1)
    
    # Guardar CSV en la carpeta transform/
    safe_print(f"\nGuardando CSV en {script_dir}:")
    logger.info(f"Guardando archivos CSV en: {script_dir}")
    
    try:
        guardar_csvs(df_ccaa, df_provincias, df_municipios, script_dir)
    except Exception as e:
        safe_print(f"ERROR guardando CSV: {e}")
        logger.error(f"Error guardando CSV: {e}", exc_info=True)
        sys.exit(1)
    
    # Resumen final en log
    logger.info("=" * 50)
    logger.info("RESUMEN DE TRANSFORMACIÓN")
    logger.info("=" * 50)
    logger.info(f"Archivo de entrada: {excel_path.name}")
    logger.info(f"Tamaño entrada: {input_size:,} bytes")
    logger.info("Archivos generados:")
    logger.info(f"  1. comunidades_autonomas.csv: {len(df_ccaa)} registros")
    logger.info(f"  2. provincias.csv: {len(df_provincias)} registros")
    logger.info(f"  3. municipios.csv: {len(df_municipios):,} registros")
    logger.info(f"Total registros transformados: {len(df_ccaa) + len(df_provincias) + len(df_municipios):,}")
    logger.info("=" * 50)
    
    safe_print("\n" + "=" * 80)
    safe_print("TRANSFORMACIÓN COMPLETADA EXITOSAMENTE")
    safe_print("=" * 80)
    
    logger.info("TRANSFORMACIÓN COMPLETADA EXITOSAMENTE")
    
    return df_ccaa, df_provincias, df_municipios


if __name__ == '__main__':
    transformar_geografia()