#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para poblar las tablas de geografía (Comunidades Autónomas, Provincias y Municipios)
usando datos oficiales del INE (Instituto Nacional de Estadística).

Fuente: INE - Relación de municipios y sus códigos por provincias
URL: https://www.ine.es/daco/daco42/codmun/codmunmapa.htm
Dataset: https://www.ine.es/daco/daco42/codmun/diccionario24.xlsx

IMPORTANTE:
- Los datos del INE son la fuente oficial del Estado Español
- Los códigos INE son únicos y permanentes
- Se actualizan anualmente con altas/bajas de municipios
"""

import asyncio
import sys
import os
from pathlib import Path
import pandas as pd
import requests
from datetime import datetime
from uuid import uuid4

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sipi_core.db.sessions import async_session_maker
from sipi_core.models.geografia import ComunidadAutonoma, Provincia, Municipio
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

# URL del dataset oficial del INE (actualizado a 2024)
INE_MUNICIPIOS_URL = "https://www.ine.es/daco/daco42/codmun/diccionario24.xlsx"

# Mapeo manual de códigos de CC.AA. del INE a nombres oficiales
# Fuente: https://www.ine.es/daco/daco42/codmun/cod_ccaa_provincia.htm
CCAA_DATOS = {
    "01": {"nombre": "Andalucía", "nombre_oficial": "Andalucía", "capital": "Sevilla"},
    "02": {"nombre": "Aragón", "nombre_oficial": "Aragón", "capital": "Zaragoza"},
    "03": {"nombre": "Asturias", "nombre_oficial": "Principado de Asturias", "capital": "Oviedo"},
    "04": {"nombre": "Baleares", "nombre_oficial": "Illes Balears", "capital": "Palma de Mallorca"},
    "05": {"nombre": "Canarias", "nombre_oficial": "Canarias", "capital": "Santa Cruz de Tenerife / Las Palmas de Gran Canaria"},
    "06": {"nombre": "Cantabria", "nombre_oficial": "Cantabria", "capital": "Santander"},
    "07": {"nombre": "Castilla y León", "nombre_oficial": "Castilla y León", "capital": "Valladolid"},
    "08": {"nombre": "Castilla-La Mancha", "nombre_oficial": "Castilla-La Mancha", "capital": "Toledo"},
    "09": {"nombre": "Cataluña", "nombre_oficial": "Catalunya", "capital": "Barcelona"},
    "10": {"nombre": "Comunidad Valenciana", "nombre_oficial": "Comunitat Valenciana", "capital": "Valencia"},
    "11": {"nombre": "Extremadura", "nombre_oficial": "Extremadura", "capital": "Mérida"},
    "12": {"nombre": "Galicia", "nombre_oficial": "Galicia", "capital": "Santiago de Compostela"},
    "13": {"nombre": "Madrid", "nombre_oficial": "Comunidad de Madrid", "capital": "Madrid"},
    "14": {"nombre": "Murcia", "nombre_oficial": "Región de Murcia", "capital": "Murcia"},
    "15": {"nombre": "Navarra", "nombre_oficial": "Comunidad Foral de Navarra", "capital": "Pamplona"},
    "16": {"nombre": "País Vasco", "nombre_oficial": "Euskadi", "capital": "Vitoria-Gasteiz"},
    "17": {"nombre": "La Rioja", "nombre_oficial": "La Rioja", "capital": "Logroño"},
    "18": {"nombre": "Ceuta", "nombre_oficial": "Ceuta", "capital": "Ceuta"},
    "19": {"nombre": "Melilla", "nombre_oficial": "Melilla", "capital": "Melilla"},
}



async def descargar_datos_ine():
    """Descarga el dataset oficial del INE"""
    print("📥 Descargando datos del INE...")
    print(f"   URL: {INE_MUNICIPIOS_URL}")

    try:
        response = requests.get(INE_MUNICIPIOS_URL, timeout=30)
        response.raise_for_status()

        # Guardar temporalmente
        temp_file = Path(__file__).parent / "temp_ine_municipios.xlsx"
        with open(temp_file, 'wb') as f:
            f.write(response.content)

        print(f"✅ Datos descargados: {len(response.content) / 1024:.1f} KB")
        return temp_file

    except Exception as e:
        print(f"❌ Error descargando datos del INE: {e}")
        print("   Verifica la conexión a Internet y que la URL esté accesible")
        sys.exit(1)


async def procesar_datos_ine(excel_file):
    """Procesa el archivo Excel del INE y extrae los datos"""
    print("\n📊 Procesando datos del INE...")

    try:
        # Leer el Excel del INE
        # El formato suele ser: CPRO | CMUN | DC | NOMBRE
        # Donde CPRO son los 2 primeros dígitos (provincia)
        # Y CPRO+CMUN forman el código completo del municipio
        df = pd.read_excel(excel_file, dtype=str)

        # Normalizar nombres de columnas
        df.columns = df.columns.str.strip().str.upper()

        print(f"   Columnas encontradas: {list(df.columns)}")
        print(f"   Total de registros: {len(df)}")

        # Extraer datos únicos de comunidades autónomas
        ccaa_set = set()
        provincias_dict = {}
        municipios_list = []

        for _, row in df.iterrows():
            # El código de provincia son los 2 primeros dígitos
            cod_provincia = str(row.get('CPRO', '')).zfill(2)
            cod_municipio_completo = str(row.get('CPRO', '')).zfill(2) + str(row.get('CMUN', '')).zfill(3)
            nombre_municipio = row.get('NOMBRE', '').strip()

            # Determinar CC.AA. por código de provincia
            # Mapeo provincia -> CC.AA.
            provincia_a_ccaa = {
                "04": "01", "11": "01", "14": "01", "18": "01", "21": "01", "23": "01", "29": "01", "41": "01",  # Andalucía
                "22": "02", "44": "02", "50": "02",  # Aragón
                "33": "03",  # Asturias
                "07": "04",  # Baleares
                "35": "05", "38": "05",  # Canarias
                "39": "06",  # Cantabria
                "05": "07", "09": "07", "24": "07", "34": "07", "37": "07", "40": "07", "42": "07", "47": "07", "49": "07",  # Castilla y León
                "02": "08", "13": "08", "16": "08", "19": "08", "45": "08",  # Castilla-La Mancha
                "08": "09", "17": "09", "25": "09", "43": "09",  # Cataluña
                "03": "10", "12": "10", "46": "10",  # C. Valenciana
                "06": "11", "10": "11",  # Extremadura
                "15": "12", "27": "12", "32": "12", "36": "12",  # Galicia
                "28": "13",  # Madrid
                "30": "14",  # Murcia
                "31": "15",  # Navarra
                "01": "16", "20": "16", "48": "16",  # País Vasco
                "26": "17",  # La Rioja
                "51": "18",  # Ceuta
                "52": "19",  # Melilla
            }

            cod_ccaa = provincia_a_ccaa.get(cod_provincia, "")

            if cod_ccaa:
                ccaa_set.add(cod_ccaa)

                if cod_provincia not in provincias_dict:
                    provincias_dict[cod_provincia] = {
                        'codigo': cod_provincia,
                        'codigo_ccaa': cod_ccaa,
                        'nombre': row.get('NOMBRE_PROVINCIA', '').strip() if 'NOMBRE_PROVINCIA' in row else '',
                        'municipios': []
                    }

                municipios_list.append({
                    'codigo_ine': cod_municipio_completo,
                    'nombre': nombre_municipio,
                    'codigo_provincia': cod_provincia,
                    'codigo_ccaa': cod_ccaa
                })

        print(f"✅ Procesados:")
        print(f"   - {len(ccaa_set)} Comunidades Autónomas")
        print(f"   - {len(provincias_dict)} Provincias")
        print(f"   - {len(municipios_list)} Municipios")

        return list(ccaa_set), list(provincias_dict.values()), municipios_list

    except Exception as e:
        print(f"❌ Error procesando datos: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


async def insertar_comunidades_autonomas(session, codigos_ccaa):
    """Inserta las comunidades autónomas en la base de datos"""
    print("\n🏛️  Insertando Comunidades Autónomas...")

    insertadas = 0
    existentes = 0

    for codigo_ccaa in codigos_ccaa:
        if codigo_ccaa not in CCAA_DATOS:
            print(f"   ⚠️  Código CC.AA. no mapeado: {codigo_ccaa}")
            continue

        datos = CCAA_DATOS[codigo_ccaa]

        # Verificar si ya existe
        result = await session.execute(
            select(ComunidadAutonoma).where(ComunidadAutonoma.codigo_ine == codigo_ccaa)
        )
        ccaa_existente = result.scalar_one_or_none()

        if ccaa_existente:
            existentes += 1
            continue

        # Crear nueva
        ccaa = ComunidadAutonoma(
            id=str(uuid4()),
            codigo_ine=codigo_ccaa,
            nombre=datos["nombre"],
            nombre_oficial=datos["nombre_oficial"],
            capital=datos["capital"],
            activo=True
        )

        session.add(ccaa)
        insertadas += 1
        print(f"   ✅ {datos['nombre']} ({codigo_ccaa})")

    await session.commit()

    print(f"\n   Total: {insertadas} insertadas, {existentes} ya existían")
    return insertadas


async def insertar_provincias(session, provincias_data):
    """Inserta las provincias en la base de datos"""
    print("\n🗺️  Insertando Provincias...")

    # Primero obtenemos todas las CC.AA. para hacer el mapeo
    result = await session.execute(select(ComunidadAutonoma))
    ccaa_dict = {ccaa.codigo_ine: ccaa.id for ccaa in result.scalars().all()}

    # Nombres oficiales de provincias
    nombres_provincias = {
        "01": "Álava", "02": "Albacete", "03": "Alicante", "04": "Almería",
        "05": "Ávila", "06": "Badajoz", "07": "Baleares", "08": "Barcelona",
        "09": "Burgos", "10": "Cáceres", "11": "Cádiz", "12": "Castellón",
        "13": "Ciudad Real", "14": "Córdoba", "15": "A Coruña", "16": "Cuenca",
        "17": "Girona", "18": "Granada", "19": "Guadalajara", "20": "Gipuzkoa",
        "21": "Huelva", "22": "Huesca", "23": "Jaén", "24": "León",
        "25": "Lleida", "26": "La Rioja", "27": "Lugo", "28": "Madrid",
        "29": "Málaga", "30": "Murcia", "31": "Navarra", "32": "Ourense",
        "33": "Asturias", "34": "Palencia", "35": "Las Palmas", "36": "Pontevedra",
        "37": "Salamanca", "38": "Santa Cruz de Tenerife", "39": "Cantabria",
        "40": "Segovia", "41": "Sevilla", "42": "Soria", "43": "Tarragona",
        "44": "Teruel", "45": "Toledo", "46": "Valencia", "47": "Valladolid",
        "48": "Bizkaia", "49": "Zamora", "50": "Zaragoza", "51": "Ceuta",
        "52": "Melilla"
    }

    insertadas = 0
    existentes = 0

    for prov_data in provincias_data:
        codigo = prov_data['codigo']
        codigo_ccaa = prov_data['codigo_ccaa']

        if codigo_ccaa not in ccaa_dict:
            print(f"   ⚠️  CC.AA. no encontrada para provincia {codigo}")
            continue

        # Verificar si ya existe
        result = await session.execute(
            select(Provincia).where(Provincia.codigo_ine == codigo)
        )
        prov_existente = result.scalar_one_or_none()

        if prov_existente:
            existentes += 1
            continue

        nombre = nombres_provincias.get(codigo, f"Provincia {codigo}")

        provincia = Provincia(
            id=str(uuid4()),
            codigo_ine=codigo,
            nombre=nombre,
            nombre_oficial=nombre,
            capital=nombre,  # Por simplicidad, usamos el mismo nombre
            comunidad_autonoma_id=ccaa_dict[codigo_ccaa],
            activo=True
        )

        session.add(provincia)
        insertadas += 1
        print(f"   ✅ {nombre} ({codigo})")

    await session.commit()

    print(f"\n   Total: {insertadas} insertadas, {existentes} ya existían")
    return insertadas


async def insertar_municipios(session, municipios_data):
    """Inserta los municipios en la base de datos"""
    print(f"\n🏘️  Insertando {len(municipios_data)} Municipios...")
    print("   (Esto puede tardar varios minutos...)")

    # Obtener mapeos
    result_ccaa = await session.execute(select(ComunidadAutonoma))
    ccaa_dict = {ccaa.codigo_ine: ccaa.id for ccaa in result_ccaa.scalars().all()}

    result_prov = await session.execute(select(Provincia))
    prov_dict = {prov.codigo_ine: prov.id for prov in result_prov.scalars().all()}

    insertados = 0
    existentes = 0
    errores = 0

    for i, mun_data in enumerate(municipios_data, 1):
        if i % 500 == 0:
            print(f"   Procesados {i}/{len(municipios_data)} municipios...")

        codigo_ine = mun_data['codigo_ine']
        codigo_provincia = mun_data['codigo_provincia']
        codigo_ccaa = mun_data['codigo_ccaa']

        if codigo_ccaa not in ccaa_dict or codigo_provincia not in prov_dict:
            errores += 1
            continue

        # Verificar si ya existe
        result = await session.execute(
            select(Municipio).where(Municipio.codigo_ine == codigo_ine)
        )
        mun_existente = result.scalar_one_or_none()

        if mun_existente:
            existentes += 1
            continue

        municipio = Municipio(
            id=str(uuid4()),
            codigo_ine=codigo_ine,
            nombre=mun_data['nombre'],
            nombre_oficial=mun_data['nombre'],
            provincia_id=prov_dict[codigo_provincia],
            comunidad_autonoma_id=ccaa_dict[codigo_ccaa],
            activo=True
        )

        session.add(municipio)
        insertados += 1

        # Commit cada 1000 registros para evitar memoria excesiva
        if insertados % 1000 == 0:
            await session.commit()
            print(f"   💾 Guardados {insertados} municipios...")

    # Commit final
    await session.commit()

    print(f"\n   Total: {insertados} insertados, {existentes} ya existían, {errores} errores")
    return insertados


async def main():
    """Función principal"""
    print("=" * 80)
    print("🇪🇸 POBLAMIENTO DE GEOGRAFÍA - DATOS OFICIALES INE")
    print("=" * 80)
    print(f"Inicio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. Descargar datos
    excel_file = await descargar_datos_ine()

    # 2. Procesar datos
    ccaa_codigos, provincias_data, municipios_data = await procesar_datos_ine(excel_file)

    # 3. Conectar a la base de datos
    print("\n🔌 Conectando a la base de datos...")
    async with async_session_maker() as session:
        # 4. Insertar datos
        ccaa_insertadas = await insertar_comunidades_autonomas(session, ccaa_codigos)
        prov_insertadas = await insertar_provincias(session, provincias_data)
        mun_insertados = await insertar_municipios(session, municipios_data)

    # 5. Limpiar archivo temporal
    if excel_file.exists():
        excel_file.unlink()
        print("\n🗑️  Archivo temporal eliminado")

    # 6. Resumen final
    print("\n" + "=" * 80)
    print("✅ POBLAMIENTO COMPLETADO")
    print("=" * 80)
    print(f"Comunidades Autónomas insertadas: {ccaa_insertadas}")
    print(f"Provincias insertadas: {prov_insertadas}")
    print(f"Municipios insertados: {mun_insertados}")
    print(f"\nFin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
