#!/usr/bin/env python3
"""
Script de inicialización de la Base de Datos para ETL.
Carga los esquemas SQL definidos en el proyecto 'sipi-etl' en la base de datos.

Usa la configuración de base de datos de sipi-core.
"""

import sys
import asyncio
from pathlib import Path
from sqlalchemy import text

# Agregar sipi-core al path
script_dir = Path(__file__).parent
SIPI_CORE_PATH = script_dir.parent.parent.parent / "sipi-core"
sys.path.insert(0, str(SIPI_CORE_PATH / "src"))

# Importar db_manager ya configurado
from sipi_core.db.sessions.async_session import db_manager

# Proyecto sipi-etl hermano
etl_project_root = script_dir.parent.parent.parent / 'sipi-etl'

async def run_sql_file(conn, file_path):
    print(f"📄 Ejecutando: {file_path.name}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
            # SQLAlchemy text() maneja múltiples sentencias
            await conn.execute(text(sql_content))
            await conn.commit()
            print("  ✅ OK")
    except Exception as e:
        print(f"  ❌ Error: {e}")

async def main():
    if not etl_project_root.exists():
        print(f"❌ No se encuentra el proyecto sipi-etl en: {etl_project_root}")
        return

    sql_dir = etl_project_root / 'sql'
    if not sql_dir.exists():
        print(f"❌ No se encuentra el directorio SQL en: {sql_dir}")
        return

    # Usar engine ya configurado de sipi-core
    engine = db_manager.engine

    print(f"🔌 Conectando a BD usando sipi-core...")
    
    # Orden de ejecución importante
    files_to_run = [
        'init.sql',
        'portals_schema.sql',
        'matching_schema.sql'
        # Añadir otros si necesarios
    ]

    async with engine.connect() as conn:
        for filename in files_to_run:
            file_path = sql_dir / filename
            if file_path.exists():
                await run_sql_file(conn, file_path)
            else:
                print(f"⚠️  No encontrado: {filename}")

    print("\n🏁 Inicialización de esquemas ETL completada.")

async def run():
    try:
        await main()
    finally:
        await db_manager.close()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run())
