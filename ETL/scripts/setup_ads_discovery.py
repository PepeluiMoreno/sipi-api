#!/usr/bin/env python3
"""
Script de inicialización de la Base de Datos para ETL.
Carga los esquemas SQL definidos en el proyecto 'sipi-etl' en la base de datos de 'sipi-api'.
"""

import sys
import os
import asyncio
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Configurar Paths
script_dir = Path(__file__).parent # ETL/loaders
project_root = script_dir.parents[1] # sipi-api
etl_project_root = project_root.parent / 'sipi-etl' # sipi-etl hermano

sys.path.append(str(project_root))
from app.core.config import settings

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

    # Ajustar conexión local
    DB_URL = settings.DATABASE_URL.replace("db", "localhost") if "db" in settings.DATABASE_URL else settings.DATABASE_URL
    engine = create_async_engine(DB_URL, echo=True)

    print(f"🔌 Conectando a BD: {DB_URL.split('@')[-1]}") # Ocultar credenciales
    
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

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
