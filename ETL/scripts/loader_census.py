#!/usr/bin/env python3
"""
Extreme Performance Bulk Loader for SIPI Census.
Uses PostgreSQL COPY protocol (via asyncpg) for near-instant loading.
"""

import sys
import os
import asyncio
import pandas as pd
import uuid
from pathlib import Path
from datetime import datetime, timezone
import asyncpg

# 1. Path Setup
script_dir = Path(__file__).parent
project_root = script_dir.parents[1]
sys.path.append(str(project_root))

from app.core.config import settings

def clean_value(val):
    if pd.isna(val) or val == '' or str(val).lower() == 'nan':
        return None
    return str(val).strip()

class CensusBulkLoader:
    def __init__(self, dsn):
        self.dsn = dsn
        self.ca_cache = {}    # Name -> ID
        self.prov_cache = {}  # Name -> ID
        self.muni_cache = {}  # (Name, ProvID) -> ID
        self.reg_cache = {}   # Name -> ID

    async def load_caches(self, conn):
        print("🧠 Cargando diccionarios geográficos...")
        # CAs
        rows = await conn.fetch("SELECT id, nombre FROM comunidades_autonomas")
        self.ca_cache = {r['nombre']: r['id'] for r in rows}
        
        # Provincias
        rows = await conn.fetch("SELECT id, nombre FROM provincias")
        self.prov_cache = {r['nombre']: r['id'] for r in rows}
        
        # Municipios
        rows = await conn.fetch("SELECT id, nombre, provincia_id FROM municipios")
        self.muni_cache = {(r['nombre'], r['provincia_id']): r['id'] for r in rows}

        # Registros
        rows = await conn.fetch("SELECT id, nombre FROM registros_propiedad")
        self.reg_cache = {r['nombre']: r['id'] for r in rows}

    async def process_csv(self, conn, file_path):
        print(f"📥 Procesando: {file_path.name}")
        df = pd.read_csv(file_path)
        
        col_nombre = next((c for c in df.columns if c.upper() in ['TITULO', 'BIEN', 'DENOMINACION', 'NOMBRE']), None)
        if not col_nombre: return

        inmueble_records = []
        inmat_records = []
        now = datetime.now(timezone.utc).replace(tzinfo=None) # asyncpg prefers naive if DB is naive
        
        for _, row in df.iterrows():
            ca_name = clean_value(row.get('Comunidad Autónoma'))
            prov_name = clean_value(row.get('Provincia'))
            muni_name = clean_value(row.get('Municipio'))
            reg_name = clean_value(row.get('REGISTRO'))

            ca_id = self.ca_cache.get(ca_name)
            prov_id = self.prov_cache.get(prov_name)
            muni_id = self.muni_cache.get((muni_name, prov_id))
            reg_id = self.reg_cache.get(reg_name)

            inmueble_id = str(uuid.uuid4())
            
            # Record for 'inmuebles'
            inmueble_records.append((
                inmueble_id,
                clean_value(row.get(col_nombre)) or "Inmueble Desconocido",
                ca_id,
                prov_id,
                muni_id,
                now,
                now,
                True # activo
            ))

            # Record for 'inmatriculaciones'
            inmat_records.append((
                str(uuid.uuid4()),
                inmueble_id,
                reg_id,
                clean_value(row.get('TOMO')),
                clean_value(row.get('LIBRO')),
                clean_value(row.get('FOLIO')),
                clean_value(row.get('FINCA') or row.get('NUMERO FINCA')),
                now,
                now
            ))

        # Perform the COPY
        print(f"⚡ Ejecutando COPY para {len(inmueble_records)} registros...")
        
        # Inmuebles
        await conn.copy_records_to_table(
            'inmuebles', 
            records=inmueble_records,
            columns=['id', 'nombre', 'comunidad_autonoma_id', 'provincia_id', 'municipio_id', 'created_at', 'updated_at', 'activo']
        )
        
        # Inmatriculaciones
        await conn.copy_records_to_table(
            'inmatriculaciones',
            records=inmat_records,
            columns=['id', 'inmueble_id', 'registro_propiedad_id', 'tomo', 'libro', 'folio', 'numero_finca', 'created_at', 'updated_at']
        )

        print(f"✅ Finalizado {file_path.name}")

async def main():
    # Adjust DSN for local access
    dsn = settings.DATABASE_URL.replace("db", "localhost") if "db" in settings.DATABASE_URL else settings.DATABASE_URL
    # converter asyncpg dsn (remove postgresql:// and handle driver issues if any)
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    print(f"🔌 Conectando a {dsn.split('@')[-1]}...")
    conn = await asyncpg.connect(dsn)
    
    try:
        loader = CensusBulkLoader(dsn)
        await loader.load_caches(conn)
        
        data_output_dir = script_dir.parent / 'census' / 'data' / 'output'
        csv_files = list(data_output_dir.glob("*.csv"))
        
        async with conn.transaction():
            for csv_file in csv_files:
                if csv_file.name == 'estadisticas_por_provincia.csv': continue
                await loader.process_csv(conn, csv_file)
                
    finally:
        await conn.close()
    
    print("\n🏁 Carga masiva completada exitosamente.")

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
