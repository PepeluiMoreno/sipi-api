#!/usr/bin/env python3
"""
Extreme Performance Bulk Loader for SIPI listado_cee.
Uses PostgreSQL COPY protocol (via asyncpg) for near-instant loading.

Usa la configuración de base de datos de sipi-core.
Nota: Usa asyncpg directamente para COPY protocol (más rápido para bulk inserts).
"""

import sys
import os
import asyncio
import pandas as pd
import uuid
from pathlib import Path
from datetime import datetime, timezone
import asyncpg

# Agregar sipi-core al path
script_dir = Path(__file__).parent
SIPI_CORE_PATH = script_dir.parent.parent.parent / "sipi-core"
sys.path.insert(0, str(SIPI_CORE_PATH / "src"))

# Importar configuración ya cargada de sipi-core
from sipi.db.sessions.async_session import DATABASE_URL

def clean_value(val):
    if pd.isna(val) or val == '' or str(val).lower() == 'nan':
        return None
    return str(val).strip()

class listado_ceeBulkLoader:
    def __init__(self, dsn, schema="sipi"):
        self.dsn = dsn
        self.schema = schema

        # Caches para búsqueda por nombre
        self.ca_by_name = {}      # nombre -> ID
        self.prov_by_name = {}    # nombre -> ID
        self.muni_by_name = {}    # (nombre, prov_id) -> ID
        self.reg_by_name = {}     # nombre -> ID

        # Cache para deduplicación (upsert)
        self.inmuebles_existentes = set()  # (nombre_lower, municipio_id)

        # Contadores de incidencias
        self.incidencias = {
            'ca_no_encontrada': [],
            'prov_no_encontrada': [],
            'muni_no_encontrado': [],
            'reg_no_encontrado': []
        }

        # Estadísticas de upsert
        self.upsert_stats = {
            'duplicados_omitidos': 0,
            'nuevos_insertados': 0
        }

    async def load_caches(self, conn):
        print("🧠 Cargando diccionarios geográficos...")
        
        # 1. CARGAR COMUNIDADES AUTÓNOMAS
        rows = await conn.fetch("""
            SELECT id, nombre, nombre_oficial 
            FROM comunidades_autonomas 
            WHERE activo = true
        """)
        
        for r in rows:
            # Por nombre principal
            if r['nombre']:
                self.ca_by_name[r['nombre'].lower()] = r['id']
            
            # Por nombre oficial (si es diferente)
            if r['nombre_oficial'] and r['nombre_oficial'] != r['nombre']:
                self.ca_by_name[r['nombre_oficial'].lower()] = r['id']
        
        print(f"  Comunidades Autónomas: {len(self.ca_by_name)} nombres cargados")
        
        # 2. CARGAR PROVINCIAS
        rows = await conn.fetch("""
            SELECT p.id, p.nombre, p.nombre_oficial, p.comunidad_autonoma_id
            FROM provincias p
            WHERE p.activo = true
        """)
        
        for r in rows:
            # Por nombre principal
            if r['nombre']:
                self.prov_by_name[r['nombre'].lower()] = r['id']
            
            # Por nombre oficial
            if r['nombre_oficial'] and r['nombre_oficial'] != r['nombre']:
                self.prov_by_name[r['nombre_oficial'].lower()] = r['id']
        
        print(f"  Provincias: {len(self.prov_by_name)} nombres cargados")
        
        # 3. CARGAR MUNICIPIOS
        rows = await conn.fetch("""
            SELECT m.id, m.nombre, m.nombre_oficial, m.provincia_id
            FROM municipios m
            WHERE m.activo = true
        """)
        
        for r in rows:
            # Por nombre principal + provincia_id
            key = (r['nombre'].lower(), r['provincia_id'])
            self.muni_by_name[key] = r['id']
            
            # Por nombre oficial (si es diferente)
            if r['nombre_oficial'] and r['nombre_oficial'] != r['nombre']:
                key_oficial = (r['nombre_oficial'].lower(), r['provincia_id'])
                self.muni_by_name[key_oficial] = r['id']
        
        print(f"  Municipios: {len(self.muni_by_name)} nombres cargados")
        
        # 4. CARGAR REGISTROS DE PROPIEDAD
        rows = await conn.fetch("SELECT id, nombre FROM registros_propiedad")
        for r in rows:
            self.reg_by_name[r['nombre'].lower()] = r['id']
        
        print(f"  Registros: {len(self.reg_by_name)} nombres cargados")

    async def load_existing_inmuebles(self, conn):
        """Carga inmuebles existentes para deduplicación (upsert)"""
        print("🔍 Cargando inmuebles existentes para deduplicación...")

        rows = await conn.fetch("""
            SELECT nombre, municipio_id
            FROM inmuebles
            WHERE activo = true AND municipio_id IS NOT NULL
        """)

        for r in rows:
            if r['nombre'] and r['municipio_id']:
                key = (r['nombre'].lower().strip(), r['municipio_id'])
                self.inmuebles_existentes.add(key)

        print(f"  Inmuebles existentes: {len(self.inmuebles_existentes):,}")

    def is_duplicate(self, nombre, municipio_id):
        """Verifica si un inmueble ya existe (por nombre + municipio)"""
        if not nombre or not municipio_id:
            return False
        key = (nombre.lower().strip(), municipio_id)
        return key in self.inmuebles_existentes

    def find_geographic_ids(self, ca_val, prov_val, muni_val):
        """Encuentra IDs usando nombres"""
        ca_id = None
        prov_id = None
        muni_id = None
        
        # 1. BUSCAR COMUNIDAD AUTÓNOMA
        if ca_val:
            ca_clean = clean_value(ca_val)
            if ca_clean:
                ca_id = self.ca_by_name.get(ca_clean.lower())
                if not ca_id:
                    # Registrar incidencia
                    self.incidencias['ca_no_encontrada'].append(ca_clean)
        
        # 2. BUSCAR PROVINCIA
        if prov_val:
            prov_clean = clean_value(prov_val)
            if prov_clean:
                prov_id = self.prov_by_name.get(prov_clean.lower())
                if not prov_id:
                    # Registrar incidencia
                    self.incidencias['prov_no_encontrada'].append(prov_clean)
        
        # 3. BUSCAR MUNICIPIO (necesita provincia_id)
        if muni_val and prov_id:
            muni_clean = clean_value(muni_val)
            if muni_clean:
                muni_id = self.muni_by_name.get((muni_clean.lower(), prov_id))
                if not muni_id:
                    # Registrar incidencia
                    self.incidencias['muni_no_encontrado'].append(muni_clean)
        
        return ca_id, prov_id, muni_id

    def print_incidencias(self, file_name):
        """Imprime las incidencias de este archivo"""
        print(f"\n📋 INCIDENCIAS para {file_name}:")
        
        if self.incidencias['ca_no_encontrada']:
            unique_cas = sorted(set(self.incidencias['ca_no_encontrada']))
            print(f"  ❌ Comunidades Autónomas no encontradas ({len(unique_cas)}):")
            for ca in unique_cas[:10]:  # Mostrar solo las primeras 10
                print(f"    - {ca}")
            if len(unique_cas) > 10:
                print(f"    ... y {len(unique_cas) - 10} más")
        
        if self.incidencias['prov_no_encontrada']:
            unique_provs = sorted(set(self.incidencias['prov_no_encontrada']))
            print(f"  ❌ Provincias no encontradas ({len(unique_provs)}):")
            for prov in unique_provs[:10]:
                print(f"    - {prov}")
            if len(unique_provs) > 10:
                print(f"    ... y {len(unique_provs) - 10} más")
        
        if self.incidencias['muni_no_encontrado']:
            unique_munis = sorted(set(self.incidencias['muni_no_encontrado']))
            print(f"  ❌ Municipios no encontrados ({len(unique_munis)}):")
            for muni in unique_munis[:10]:
                print(f"    - {muni}")
            if len(unique_munis) > 10:
                print(f"    ... y {len(unique_munis) - 10} más")
        
        if self.incidencias['reg_no_encontrado']:
            unique_regs = sorted(set(self.incidencias['reg_no_encontrado']))
            print(f"  ❌ Registros no encontrados ({len(unique_regs)}):")
            for reg in unique_regs[:10]:
                print(f"    - {reg}")
            if len(unique_regs) > 10:
                print(f"    ... y {len(unique_regs) - 10} más")

    async def process_csv(self, conn, file_path):
        print(f"\n📥 Procesando: {file_path.name}")
        df = pd.read_csv(file_path)
        
        # Resetear incidencias para este archivo
        self.incidencias = {k: [] for k in self.incidencias.keys()}
        
        # Detectar columnas por nombres comunes
        col_mapping = {}
        for col in df.columns:
            col_lower = str(col).lower()
            
            if any(x in col_lower for x in ['comunidad', 'autonom', 'ccaa', 'ca']):
                col_mapping['comunidad_autonoma'] = col
            
            elif any(x in col_lower for x in ['provincia', 'prov']):
                col_mapping['provincia'] = col
            
            elif any(x in col_lower for x in ['municipio', 'muni', 'localidad']):
                col_mapping['municipio'] = col
            
            elif any(x in col_lower for x in ['registro']):
                col_mapping['registro'] = col
            
            elif any(x in col_lower for x in ['título', 'titulo', 'bien', 'denominacion', 'nombre', 'descripcion']):
                col_mapping['nombre_inmueble'] = col
        
        print(f"  🔍 Columnas detectadas:")
        for key, col in col_mapping.items():
            print(f"    - {key}: {col}")
        
        if 'nombre_inmueble' not in col_mapping:
            print(f"  ⚠️  No se encontró columna de nombre del inmueble")
            return
        
        inmueble_records = []
        inmat_records = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        total_rows = len(df)
        registros_con_errores = 0
        
        for idx, row in df.iterrows():
            # Obtener valores
            ca_val = row.get(col_mapping.get('comunidad_autonoma'))
            prov_val = row.get(col_mapping.get('provincia'))
            muni_val = row.get(col_mapping.get('municipio'))
            reg_val = row.get(col_mapping.get('registro'))
            
            # Encontrar IDs usando nombres
            ca_id, prov_id, muni_id = self.find_geographic_ids(ca_val, prov_val, muni_val)
            
            # Buscar registro por nombre
            reg_id = None
            if reg_val:
                reg_clean = clean_value(reg_val)
                if reg_clean:
                    reg_id = self.reg_by_name.get(reg_clean.lower())
                    if not reg_id:
                        self.incidencias['reg_no_encontrado'].append(reg_clean)
            
            # Verificar si este registro tiene errores
            tiene_errores = False
            if ca_val and not ca_id:
                tiene_errores = True
            if prov_val and not prov_id:
                tiene_errores = True
            if muni_val and not muni_id:
                tiene_errores = True
            if reg_val and not reg_id:
                tiene_errores = True
            
            if tiene_errores:
                registros_con_errores += 1
                # Saltar este registro si tiene errores
                continue
            
            # Record for 'inmuebles'
            nombre_inmueble = clean_value(row.get(col_mapping['nombre_inmueble'])) or "Inmueble Desconocido"

            # UPSERT: Verificar si ya existe este inmueble
            if self.is_duplicate(nombre_inmueble, muni_id):
                self.upsert_stats['duplicados_omitidos'] += 1
                continue  # Omitir duplicado

            inmueble_id = str(uuid.uuid4())
            inmueble_records.append((
                inmueble_id,
                nombre_inmueble,
                ca_id,
                prov_id,
                muni_id,
                now,
                now,
                True  # activo
            ))

            # Agregar a cache para evitar duplicados dentro del mismo CSV
            key = (nombre_inmueble.lower().strip(), muni_id)
            self.inmuebles_existentes.add(key)

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

            self.upsert_stats['nuevos_insertados'] += 1
            
            # Mostrar progreso cada 1000 registros
            if (idx + 1) % 1000 == 0:
                print(f"  Procesados {idx + 1:,}/{total_rows:,} registros")

        # Estadísticas del archivo
        print(f"\n  📊 Estadísticas de {file_path.name}:")
        print(f"    - Total registros en CSV: {total_rows:,}")
        print(f"    - Registros nuevos a insertar: {len(inmueble_records):,}")
        print(f"    - Duplicados omitidos (upsert): {self.upsert_stats['duplicados_omitidos']:,}")
        print(f"    - Registros con errores: {registros_con_errores:,}")
        
        if registros_con_errores > 0:
            print(f"    - Porcentaje exitoso: {(len(inmueble_records)/total_rows)*100:.1f}%")
        
        # Imprimir incidencias
        self.print_incidencias(file_path.name)
        
        # Si no hay registros para procesar, salir
        if not inmueble_records:
            print(f"  ⚠️  No hay registros válidos para procesar en {file_path.name}")
            return
        
        # Perform the COPY
        print(f"  ⚡ Ejecutando COPY para {len(inmueble_records)} registros...")

        try:
            # Inmuebles
            await conn.copy_records_to_table(
                'inmuebles',
                records=inmueble_records,
                columns=['id', 'nombre', 'comunidad_autonoma_id', 'provincia_id', 'municipio_id', 'created_at', 'updated_at', 'activo'],
                schema_name=self.schema
            )

            # Inmatriculaciones
            await conn.copy_records_to_table(
                'inmatriculaciones',
                records=inmat_records,
                columns=['id', 'inmueble_id', 'registro_propiedad_id', 'tomo', 'libro', 'folio', 'numero_finca', 'created_at', 'updated_at'],
                schema_name=self.schema
            )

            print(f"  ✅ {file_path.name} cargado exitosamente")
        except Exception as e:
            print(f"  ❌ Error en COPY: {e}")
            raise

async def main():
    # Usar DATABASE_URL ya configurado por sipi-core
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no configurado")
        return

    # Convertir asyncpg a postgresql estándar para asyncpg raw
    dsn = DATABASE_URL
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    schema = os.getenv("DATABASE_SCHEMA", "sipi")

    print(f"🔌 Conectando a {dsn.split('@')[-1]}...")
    conn = await asyncpg.connect(dsn)

    try:
        # Establecer search_path al schema
        await conn.execute(f"SET search_path TO {schema}, public")

        loader = listado_ceeBulkLoader(dsn, schema)
        await loader.load_caches(conn)
        await loader.load_existing_inmuebles(conn)  # Cargar para upsert
        
        data_output_dir = script_dir.parent / 'census' / 'data' / 'output'
        csv_files = list(data_output_dir.glob("*.csv"))
        
        if not csv_files:
            print(f"❌ No se encontraron archivos CSV en {data_output_dir}")
            return
        
        print(f"📁 Encontrados {len(csv_files)} archivos CSV:")
        for csv_file in csv_files:
            print(f"  - {csv_file.name}")
        
        # Procesar cada archivo en su propia transacción
        for csv_file in csv_files:
            if csv_file.name == 'estadisticas_por_provincia.csv': 
                continue
            
            async with conn.transaction():
                await loader.process_csv(conn, csv_file)
                
    except Exception as e:
        print(f"❌ Error durante la carga: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        await conn.close()
    
    print("\n🏁 Carga completada exitosamente.")
    print(f"\n📊 Resumen upsert:")
    print(f"   - Nuevos insertados: {loader.upsert_stats['nuevos_insertados']:,}")
    print(f"   - Duplicados omitidos: {loader.upsert_stats['duplicados_omitidos']:,}")

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())