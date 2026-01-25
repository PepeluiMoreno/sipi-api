#!/usr/bin/env python3
"""
Script para descargar y procesar datos geográficos oficiales del INE

FUENTE: Instituto Nacional de Estadística
URL: https://www.ine.es/daco/daco42/codmun/diccionario24.xlsx
"""

import pandas as pd
import requests
import os
import sys
from pathlib import Path
from datetime import datetime
import asyncio
import asyncpg
import uuid
from dotenv import load_dotenv

load_dotenv()

INE_URLS = {
    '2024': 'https://www.ine.es/daco/daco42/codmun/diccionario24.xlsx',
    '2023': 'https://www.ine.es/daco/daco42/codmun/diccionario23.xlsx',
}

CCAA_OFICIAL = {
    '01': 'Andalucía',
    '02': 'Aragón',
    '03': 'Asturias, Principado de',
    '04': 'Balears, Illes',
    '05': 'Canarias',
    '06': 'Cantabria',
    '07': 'Castilla y León',
    '08': 'Castilla-La Mancha',
    '09': 'Cataluña',
    '10': 'Comunitat Valenciana',
    '11': 'Extremadura',
    '12': 'Galicia',
    '13': 'Madrid, Comunidad de',
    '14': 'Murcia, Región de',
    '15': 'Navarra, Comunidad Foral de',
    '16': 'País Vasco',
    '17': 'Rioja, La',
    '18': 'Ceuta',
    '19': 'Melilla',
}

PROVINCIA_A_CCAA = {
    '04': '01', '11': '01', '14': '01', '18': '01', '21': '01', '23': '01', '29': '01', '41': '01',
    '22': '02', '44': '02', '50': '02',
    '33': '03',
    '07': '04',
    '35': '05', '38': '05',
    '39': '06',
    '05': '07', '09': '07', '24': '07', '34': '07', '37': '07', '40': '07', '42': '07', '47': '07', '49': '07',
    '02': '08', '13': '08', '16': '08', '19': '08', '45': '08',
    '08': '09', '17': '09', '25': '09', '43': '09',
    '03': '10', '12': '10', '46': '10',
    '06': '11', '10': '11',
    '15': '12', '27': '12', '32': '12', '36': '12',
    '28': '13',
    '30': '14',
    '31': '15',
    '01': '16', '20': '16', '48': '16',
    '26': '17',
    '51': '18',
    '52': '19',
}

NOMBRES_PROVINCIAS = {
    '01': 'Araba/Álava', '02': 'Albacete', '03': 'Alicante/Alacant', '04': 'Almería',
    '05': 'Ávila', '06': 'Badajoz', '07': 'Balears, Illes', '08': 'Barcelona',
    '09': 'Burgos', '10': 'Cáceres', '11': 'Cádiz', '12': 'Castellón/Castelló',
    '13': 'Ciudad Real', '14': 'Córdoba', '15': 'Coruña, A', '16': 'Cuenca',
    '17': 'Girona', '18': 'Granada', '19': 'Guadalajara', '20': 'Gipuzkoa',
    '21': 'Huelva', '22': 'Huesca', '23': 'Jaén', '24': 'León',
    '25': 'Lleida', '26': 'Rioja, La', '27': 'Lugo', '28': 'Madrid',
    '29': 'Málaga', '30': 'Murcia', '31': 'Navarra', '32': 'Ourense',
    '33': 'Asturias', '34': 'Palencia', '35': 'Palmas, Las', '36': 'Pontevedra',
    '37': 'Salamanca', '38': 'Santa Cruz de Tenerife', '39': 'Cantabria', '40': 'Segovia',
    '41': 'Sevilla', '42': 'Soria', '43': 'Tarragona', '44': 'Teruel',
    '45': 'Toledo', '46': 'Valencia/València', '47': 'Valladolid', '48': 'Bizkaia',
    '49': 'Zamora', '50': 'Zaragoza', '51': 'Ceuta', '52': 'Melilla',
}


def descargar_excel_ine(output_path):
    print("Descargando datos del INE...")
    for year, url in sorted(INE_URLS.items(), reverse=True):
        try:
            print(f"  Intentando {year}: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                f.write(response.content)
            print(f"  Descarga exitosa: {len(response.content) / 1024:.2f} KB")
            return True
        except requests.exceptions.RequestException as e:
            print(f"  Error: {e}")
            continue
    print("  ERROR: No se pudo descargar")
    return False


def generar_csv_ccaa(output_path):
    print("\nGenerando CSV de Comunidades Autonomas...")
    data = []
    for codigo, nombre in CCAA_OFICIAL.items():
        data.append({
            'codigo_ine': codigo,
            'nombre': nombre,
            'nombre_oficial': nombre,
            'activo': True
        })
    df = pd.DataFrame(data).sort_values('codigo_ine')
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"  CSV guardado: {output_path} ({len(df)} registros)")
    return df


def procesar_excel_ine(excel_path, output_provincias, output_municipios):
    print("\nProcesando Excel del INE...")
    df = pd.read_excel(excel_path, header=1)
    print(f"  Registros: {len(df)}")

    col_provincia = None
    col_municipio = None
    col_nombre = None

    for col in df.columns:
        col_upper = str(col).upper()
        if 'CPRO' in col_upper or col_upper == 'PROVINCIA':
            col_provincia = col
        elif 'CMUN' in col_upper or col_upper == 'MUNICIPIO':
            col_municipio = col
        elif 'NOMBRE' in col_upper or col_upper == 'LITERAL':
            col_nombre = col

    if not all([col_provincia, col_municipio, col_nombre]):
        print(f"  ERROR: Columnas no detectadas")
        return None, None

    df[col_provincia] = df[col_provincia].astype(str).str.zfill(2)
    df[col_municipio] = df[col_municipio].astype(str).str.zfill(3)
    df['codigo_completo'] = df[col_provincia] + df[col_municipio]

    # PROVINCIAS
    print("\nGenerando CSV de Provincias...")
    provincias_unicas = df[[col_provincia]].drop_duplicates()
    data_provincias = []
    for _, row in provincias_unicas.iterrows():
        codigo_prov = row[col_provincia]
        nombre_provincia = NOMBRES_PROVINCIAS.get(codigo_prov, f'Provincia {codigo_prov}')
        codigo_ccaa = PROVINCIA_A_CCAA.get(codigo_prov, '00')
        data_provincias.append({
            'codigo_ine': codigo_prov,
            'nombre': nombre_provincia,
            'nombre_oficial': nombre_provincia,
            'comunidad_autonoma_codigo': codigo_ccaa,
            'activo': True
        })

    df_provincias = pd.DataFrame(data_provincias).sort_values('codigo_ine')
    df_provincias.to_csv(output_provincias, index=False, encoding='utf-8')
    print(f"  CSV guardado: {output_provincias} ({len(df_provincias)} registros)")

    # MUNICIPIOS
    print("\nGenerando CSV de Municipios...")
    data_municipios = []
    for _, row in df.iterrows():
        codigo_prov = row[col_provincia]
        codigo_completo = row['codigo_completo']
        nombre = str(row[col_nombre]).strip()
        data_municipios.append({
            'codigo_ine': codigo_completo,
            'nombre': nombre,
            'nombre_oficial': nombre,
            'provincia_codigo': codigo_prov,
            'activo': True
        })

    df_municipios = pd.DataFrame(data_municipios).sort_values('codigo_ine')
    df_municipios.to_csv(output_municipios, index=False, encoding='utf-8')
    print(f"  CSV guardado: {output_municipios} ({len(df_municipios)} registros)")

    return df_provincias, df_municipios


async def ejecutar_seeding_directo(csv_ccaa, csv_provincias, csv_municipios):
    print("\nEjecutando seeding en base de datos...")
    database_url = os.getenv('DATABASE_URL')
    schema = os.getenv('DATABASE_SCHEMA', 'sipi')

    if not database_url:
        print("  ERROR: DATABASE_URL no configurado")
        return False

    database_url = database_url.replace('postgresql+asyncpg://', 'postgresql://')

    try:
        conn = await asyncpg.connect(database_url)
        print(f"  Conectado (schema: {schema})")
        await conn.execute(f'SET search_path TO {schema}')

        # CCAA
        print("\n  Cargando Comunidades Autonomas...")
        df_ccaa = pd.read_csv(csv_ccaa)
        for _, row in df_ccaa.iterrows():
            await conn.execute('''
                INSERT INTO comunidades_autonomas (id, codigo_ine, nombre, nombre_oficial, activo, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, NOW(), NOW())
                ON CONFLICT (codigo_ine) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    updated_at = NOW()
            ''', str(uuid.uuid4()), str(row['codigo_ine']), str(row['nombre']), str(row['nombre_oficial']), bool(row['activo']))

        count_ccaa = await conn.fetchval(f'SELECT COUNT(*) FROM {schema}.comunidades_autonomas')
        print(f"    {count_ccaa} comunidades autonomas")

        # PROVINCIAS
        print("\n  Cargando Provincias...")
        df_prov = pd.read_csv(csv_provincias)
        for _, row in df_prov.iterrows():
            ccaa_id = await conn.fetchval(
                f'SELECT id FROM {schema}.comunidades_autonomas WHERE codigo_ine = $1',
                str(row['comunidad_autonoma_codigo'])
            )
            if ccaa_id:
                await conn.execute('''
                    INSERT INTO provincias (id, codigo_ine, nombre, nombre_oficial, comunidad_autonoma_id, activo, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW())
                    ON CONFLICT (codigo_ine) DO UPDATE SET
                        nombre = EXCLUDED.nombre,
                        updated_at = NOW()
                ''', str(uuid.uuid4()), str(row['codigo_ine']), str(row['nombre']), str(row['nombre_oficial']), ccaa_id, bool(row['activo']))

        count_prov = await conn.fetchval(f'SELECT COUNT(*) FROM {schema}.provincias')
        print(f"    {count_prov} provincias")

        # MUNICIPIOS
        print("\n  Cargando Municipios...")
        df_muni = pd.read_csv(csv_municipios)
        total_municipios = len(df_muni)

        # Cache provincia lookups to avoid repeated queries
        print("    Cargando cache de provincias...")
        prov_cache = {}
        provincias = await conn.fetch(f'SELECT codigo_ine, id, comunidad_autonoma_id FROM {schema}.provincias')
        for prov in provincias:
            prov_cache[prov['codigo_ine']] = (prov['id'], prov['comunidad_autonoma_id'])

        # Use executemany for batch inserts
        batch_size = 500
        valores = []

        for i, (_, row) in enumerate(df_muni.iterrows(), 1):
            codigo_prov = str(row['provincia_codigo'])
            if codigo_prov in prov_cache:
                prov_id, ccaa_id = prov_cache[codigo_prov]
                valores.append((
                    str(uuid.uuid4()),
                    str(row['codigo_ine']),
                    str(row['nombre']),
                    str(row['nombre_oficial']),
                    prov_id,
                    ccaa_id,
                    bool(row['activo'])
                ))

            # Execute batch
            if len(valores) >= batch_size or i == total_municipios:
                await conn.executemany('''
                    INSERT INTO municipios (id, codigo_ine, nombre, nombre_oficial, provincia_id, comunidad_autonoma_id, activo, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, NOW(), NOW())
                    ON CONFLICT (codigo_ine) DO NOTHING
                ''', valores)
                print(f"    Procesados {i}/{total_municipios}", end='\r')
                valores = []

        count_muni = await conn.fetchval(f'SELECT COUNT(*) FROM {schema}.municipios')
        print(f"\n    {count_muni} municipios")

        await conn.close()
        print("\n  Seeding completado")
        return True

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 80)
    print("SEEDING DE GEOGRAFIA DE ESPANA - DATOS OFICIALES INE")
    print("=" * 80)

    script_dir = Path(__file__).parent
    etl_dir = script_dir.parent
    data_dir = etl_dir / 'data'
    input_dir = data_dir / 'input'
    output_dir = data_dir / 'output'

    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    excel_path = input_dir / 'geografia_ine.xlsx'
    csv_ccaa = output_dir / 'comunidades_autonomas.csv'
    csv_provincias = output_dir / 'provincias.csv'
    csv_municipios = output_dir / 'municipios.csv'

    if not excel_path.exists():
        if not descargar_excel_ine(excel_path):
            print("\nERROR: No se pudo descargar el Excel")
            sys.exit(1)
    else:
        print(f"\nExcel ya existe: {excel_path}")

    generar_csv_ccaa(csv_ccaa)
    df_prov, df_muni = procesar_excel_ine(excel_path, csv_provincias, csv_municipios)

    if df_prov is None or df_muni is None:
        print("\nERROR: No se pudieron procesar los datos")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("EJECUTANDO SEEDING")
    print("=" * 80)

    resultado = asyncio.run(ejecutar_seeding_directo(csv_ccaa, csv_provincias, csv_municipios))

    if resultado:
        print("\n" + "=" * 80)
        print("SEEDING COMPLETADO")
        print("=" * 80)
        print(f"\nArchivos generados:")
        print(f"  - {csv_ccaa}")
        print(f"  - {csv_provincias}")
        print(f"  - {csv_municipios}")
    else:
        print("\nERROR EN SEEDING")
        sys.exit(1)


if __name__ == '__main__':
    main()
