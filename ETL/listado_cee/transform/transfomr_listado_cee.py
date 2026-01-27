#!/usr/bin/env python3
"""
load_listado_cee.py

Bulk Loader para datos de Inmatriculaciones CEE desde CSV generados.
Carga todos los archivos CSV del directorio output/ que fueron generados
por la transformación del Excel original.

Usa nombres para referencias geográficas y reporta incidencias detalladas.
Usa protocolo COPY de PostgreSQL para máxima velocidad de carga.
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
    """Limpia valores: convierte NaN/empty a None y elimina espacios"""
    if pd.isna(val) or val == '' or str(val).lower() == 'nan':
        return None
    return str(val).strip()

class InmatriculacionesCEELoader:
    """Loader para datos de inmatriculaciones CEE desde archivos CSV"""
    
    def __init__(self, dsn, schema="sipi"):
        self.dsn = dsn
        self.schema = schema
        
        # Caches para búsqueda por nombre
        self.ca_by_name = {}      # nombre -> ID
        self.prov_by_name = {}    # nombre -> ID
        self.muni_by_name = {}    # (nombre, prov_id) -> ID
        self.reg_by_name = {}     # nombre -> ID
        
        # Contadores de incidencias (acumulados para todos los archivos)
        self.incidencias_totales = {
            'ca_no_encontrada': [],
            'prov_no_encontrada': [],
            'muni_no_encontrado': [],
            'reg_no_encontrado': []
        }
        
        # Estadísticas generales
        self.estadisticas_totales = {
            'total_archivos': 0,
            'total_registros': 0,
            'registros_procesados': 0,
            'registros_con_errores': 0,
            'inmuebles_insertados': 0,
            'inmatriculaciones_insertadas': 0
        }

    async def load_caches(self, conn):
        """Carga todos los diccionarios geográficos desde la base de datos"""
        print("Cargando diccionarios geográficos...")
        
        # 1. CARGAR COMUNIDADES AUTÓNOMAS
        rows = await conn.fetch("""
            SELECT id, nombre, nombre_oficial 
            FROM comunidades_autonomas 
            WHERE activo = true
            ORDER BY nombre
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
            ORDER BY p.nombre
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
            ORDER BY m.nombre
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
        rows = await conn.fetch("""
            SELECT id, nombre 
            FROM registros_propiedad 
            ORDER BY nombre
        """)
        for r in rows:
            self.reg_by_name[r['nombre'].lower()] = r['id']
        
        print(f"  Registros: {len(self.reg_by_name)} nombres cargados")

    def find_geographic_ids(self, ca_val, prov_val, muni_val, incidencias_archivo):
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
                    incidencias_archivo['ca_no_encontrada'].append(ca_clean)
        
        # 2. BUSCAR PROVINCIA
        if prov_val:
            prov_clean = clean_value(prov_val)
            if prov_clean:
                prov_id = self.prov_by_name.get(prov_clean.lower())
                if not prov_id:
                    # Registrar incidencia
                    incidencias_archivo['prov_no_encontrada'].append(prov_clean)
        
        # 3. BUSCAR MUNICIPIO (necesita provincia_id)
        if muni_val and prov_id:
            muni_clean = clean_value(muni_val)
            if muni_clean:
                muni_id = self.muni_by_name.get((muni_clean.lower(), prov_id))
                if not muni_id:
                    # Registrar incidencia
                    incidencias_archivo['muni_no_encontrado'].append(muni_clean)
        
        return ca_id, prov_id, muni_id

    def print_incidencias_archivo(self, file_name, incidencias_archivo):
        """Imprime las incidencias de un archivo específico"""
        print(f"\n  INCIDENCIAS para {file_name}:")
        
        todas_vacias = True
        for key, lista in incidencias_archivo.items():
            if lista:
                todas_vacias = False
                unique_items = sorted(set(lista))
                
                tipo = {
                    'ca_no_encontrada': 'Comunidades Autónomas',
                    'prov_no_encontrada': 'Provincias',
                    'muni_no_encontrado': 'Municipios',
                    'reg_no_encontrado': 'Registros de Propiedad'
                }[key]
                
                print(f"\n    {tipo} no encontrados ({len(unique_items)} diferentes):")
                
                # Mostrar los primeros 5
                for item in unique_items[:5]:
                    print(f"      - '{item}'")
                
                if len(unique_items) > 5:
                    print(f"      ... y {len(unique_items) - 5} más")
        
        if todas_vacias:
            print("    No hay incidencias")

    async def process_csv(self, conn, csv_path):
        """Procesa un archivo CSV individual"""
        print(f"\nProcesando: {csv_path.name}")
        
        # Incidencias específicas para este archivo
        incidencias_archivo = {k: [] for k in self.incidencias_totales.keys()}
        
        try:
            # Leer el archivo CSV
            print(f"  Leyendo CSV...")
            df = pd.read_csv(csv_path, encoding='utf-8')
        except UnicodeDecodeError:
            # Intentar con otra codificación
            try:
                df = pd.read_csv(csv_path, encoding='latin-1')
            except Exception as e:
                print(f"  Error leyendo CSV: {e}")
                return
        except Exception as e:
            print(f"  Error leyendo CSV: {e}")
            return
        
        print(f"  Filas leídas: {len(df):,}")
        
        # Detectar columnas por nombres comunes (adaptado para CSV transformados)
        col_mapping = {}
        
        # Mapeo flexible de columnas
        columnas_esperadas = {
            'comunidad_autonoma': ['comunidad_autonoma', 'comunidad', 'ccaa', 'ca', 'autonomia'],
            'provincia': ['provincia', 'prov', 'provincias'],
            'municipio': ['municipio', 'municipios', 'localidad', 'localidades'],
            'registro': ['registro', 'registro_propiedad', 'registros', 'registro de la propiedad'],
            'nombre_inmueble': ['denominacion', 'bien', 'inmueble', 'titulo', 'nombre', 'descripcion'],
            'tomo': ['tomo', 'tomo_num', 'tomo_numero'],
            'libro': ['libro', 'libro_num', 'libro_numero'],
            'folio': ['folio', 'folio_num', 'folio_numero'],
            'finca': ['finca', 'numero_finca', 'num_finca', 'finca_numero', 'numero']
        }
        
        for col in df.columns:
            col_lower = str(col).lower().strip()
            
            # Primero intentar coincidencia exacta
            for key, posibles in columnas_esperadas.items():
                if col_lower in posibles:
                    col_mapping[key] = col
                    break
            
            # Si no encontramos, buscar por contenido
            if col not in col_mapping.values():
                for key, posibles in columnas_esperadas.items():
                    for posible in posibles:
                        if posible in col_lower:
                            col_mapping[key] = col
                            break
                    if key in col_mapping:
                        break
        
        print(f"\n  Columnas detectadas en {csv_path.name}:")
        for key in columnas_esperadas.keys():
            if key in col_mapping:
                print(f"    - {key}: '{col_mapping[key]}'")
            else:
                print(f"    - {key}: NO ENCONTRADA")
        
        # Verificar columnas esenciales
        columnas_esenciales = ['nombre_inmueble']
        faltan_esenciales = [col for col in columnas_esenciales if col not in col_mapping]
        
        if faltan_esenciales:
            print(f"\n  ERROR: Faltan columnas esenciales: {faltan_esenciales}")
            return
        
        inmueble_records = []
        inmat_records = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        registros_archivo = len(df)
        registros_procesados_archivo = 0
        registros_con_errores_archivo = 0
        
        print(f"\n  Procesando {registros_archivo:,} registros...")
        
        for idx, row in df.iterrows():
            try:
                # Obtener valores
                ca_val = row.get(col_mapping.get('comunidad_autonoma'))
                prov_val = row.get(col_mapping.get('provincia'))
                muni_val = row.get(col_mapping.get('municipio'))
                reg_val = row.get(col_mapping.get('registro'))
                
                # Encontrar IDs usando nombres
                ca_id, prov_id, muni_id = self.find_geographic_ids(ca_val, prov_val, muni_val, incidencias_archivo)
                
                # Buscar registro por nombre
                reg_id = None
                if reg_val:
                    reg_clean = clean_value(reg_val)
                    if reg_clean:
                        reg_id = self.reg_by_name.get(reg_clean.lower())
                        if not reg_id:
                            incidencias_archivo['reg_no_encontrado'].append(reg_clean)
                
                # Verificar si este registro tiene errores
                tiene_errores = False
                
                # Solo requerimos el nombre del inmueble
                # Los datos geográficos pueden ser opcionales para algunos registros
                if ca_val and not ca_id:
                    tiene_errores = True
                if prov_val and not prov_id:
                    tiene_errores = True
                if muni_val and not muni_id:
                    tiene_errores = True
                if reg_val and not reg_id:
                    tiene_errores = True
                
                if tiene_errores:
                    registros_con_errores_archivo += 1
                    continue
                
                # Todos los datos encontrados o no requeridos - crear registros
                inmueble_id = str(uuid.uuid4())
                nombre_inmueble = clean_value(row.get(col_mapping['nombre_inmueble'])) or "Inmueble Desconocido"
                
                # Limitar longitud del nombre
                if len(nombre_inmueble) > 500:
                    nombre_inmueble = nombre_inmueble[:497] + "..."
                
                # Record for 'inmuebles'
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
                
                # Obtener datos de inmatriculación (pueden ser None)
                tomo = clean_value(row.get(col_mapping.get('tomo')))
                libro = clean_value(row.get(col_mapping.get('libro')))
                folio = clean_value(row.get(col_mapping.get('folio')))
                finca = clean_value(row.get(col_mapping.get('finca')))
                
                # Record for 'inmatriculaciones'
                inmat_records.append((
                    str(uuid.uuid4()),
                    inmueble_id,
                    reg_id,
                    tomo,
                    libro,
                    folio,
                    finca,
                    now,
                    now
                ))
                
                registros_procesados_archivo += 1
                
            except Exception as e:
                print(f"  Error procesando fila {idx} en {csv_path.name}: {e}")
                registros_con_errores_archivo += 1
                continue
            
            # Mostrar progreso cada 500 registros para archivos grandes
            if (idx + 1) % 500 == 0:
                porcentaje = ((idx + 1) / registros_archivo) * 100
                print(f"    Procesados {idx + 1:,}/{registros_archivo:,} ({porcentaje:.1f}%)")
        
        # Estadísticas del archivo
        print(f"\n  ESTADÍSTICAS para {csv_path.name}:")
        print(f"    - Total registros: {registros_archivo:,}")
        print(f"    - Registros procesados: {registros_procesados_archivo:,}")
        print(f"    - Registros con errores: {registros_con_errores_archivo:,}")
        
        if registros_archivo > 0:
            porcentaje_exito = (registros_procesados_archivo / registros_archivo) * 100
            print(f"    - Porcentaje de éxito: {porcentaje_exito:.1f}%")
        
        # Imprimir incidencias de este archivo
        self.print_incidencias_archivo(csv_path.name, incidencias_archivo)
        
        # Actualizar estadísticas totales
        self.estadisticas_totales['total_registros'] += registros_archivo
        self.estadisticas_totales['registros_procesados'] += registros_procesados_archivo
        self.estadisticas_totales['registros_con_errores'] += registros_con_errores_archivo
        
        # Acumular incidencias
        for key in self.incidencias_totales.keys():
            self.incidencias_totales[key].extend(incidencias_archivo[key])
        
        # Si no hay registros para procesar, salir
        if not inmueble_records:
            print(f"\n  No hay registros válidos para procesar en {csv_path.name}")
            return False
        
        # Perform the COPY
        print(f"\n  Ejecutando COPY para {len(inmueble_records)} inmuebles...")

        try:
            # Inmuebles
            await conn.copy_records_to_table(
                'inmuebles',
                records=inmueble_records,
                columns=['id', 'nombre', 'comunidad_autonoma_id', 'provincia_id', 'municipio_id', 'created_at', 'updated_at', 'activo'],
                schema_name=self.schema
            )
            inmuebles_insertados = len(inmueble_records)
            self.estadisticas_totales['inmuebles_insertados'] += inmuebles_insertados
            print(f"    {inmuebles_insertados:,} inmuebles insertados")

            # Inmatriculaciones
            await conn.copy_records_to_table(
                'inmatriculaciones',
                records=inmat_records,
                columns=['id', 'inmueble_id', 'registro_propiedad_id', 'tomo', 'libro', 'folio', 'numero_finca', 'created_at', 'updated_at'],
                schema_name=self.schema
            )
            inmatriculaciones_insertadas = len(inmat_records)
            self.estadisticas_totales['inmatriculaciones_insertadas'] += inmatriculaciones_insertadas
            print(f"    {inmatriculaciones_insertadas:,} inmatriculaciones insertadas")

            print(f"  {csv_path.name} cargado exitosamente")
            return True
            
        except Exception as e:
            print(f"  Error en COPY para {csv_path.name}: {e}")
            return False

    def print_resumen_final(self):
        """Imprime un resumen final de toda la carga"""
        print("\n" + "=" * 80)
        print("RESUMEN FINAL DE LA CARGA")
        print("=" * 80)
        
        print(f"\nESTADÍSTICAS GENERALES:")
        print(f"  - Total archivos procesados: {self.estadisticas_totales['total_archivos']}")
        print(f"  - Total registros en CSV: {self.estadisticas_totales['total_registros']:,}")
        print(f"  - Inmuebles insertados: {self.estadisticas_totales['inmuebles_insertados']:,}")
        print(f"  - Inmatriculaciones insertadas: {self.estadisticas_totales['inmatriculaciones_insertadas']:,}")
        print(f"  - Registros con errores: {self.estadisticas_totales['registros_con_errores']:,}")
        
        if self.estadisticas_totales['total_registros'] > 0:
            porcentaje_exito = (self.estadisticas_totales['inmuebles_insertados'] / self.estadisticas_totales['total_registros']) * 100
            print(f"  - Tasa de éxito global: {porcentaje_exito:.1f}%")
        
        print(f"\nINCIDENCIAS ACUMULADAS:")
        
        for key, lista in self.incidencias_totales.items():
            if lista:
                unique_items = sorted(set(lista))
                
                tipo = {
                    'ca_no_encontrada': 'Comunidades Autónomas',
                    'prov_no_encontrada': 'Provincias',
                    'muni_no_encontrado': 'Municipios',
                    'reg_no_encontrado': 'Registros de Propiedad'
                }[key]
                
                print(f"\n  {tipo} no encontrados ({len(unique_items)} diferentes):")
                
                # Mostrar los primeros 10
                for item in unique_items[:10]:
                    print(f"    - '{item}'")
                
                if len(unique_items) > 10:
                    print(f"    ... y {len(unique_items) - 10} más")
        
        # Verificar si no hubo incidencias
        todas_vacias = all(not lista for lista in self.incidencias_totales.values())
        if todas_vacias:
            print("  No hubo incidencias en ningún archivo")
        
        print("\nRECOMENDACIONES:")
        if self.incidencias_totales['ca_no_encontrada']:
            print("  - Revisar nombres de Comunidades Autónomas en los CSV")
            print("  - Verificar tildes y mayúsculas/minúsculas")
        
        if self.incidencias_totales['prov_no_encontrada']:
            print("  - Verificar nombres de provincias (ej: 'Álava' vs 'Araba/Álava')")
        
        if self.incidencias_totales['muni_no_encontrado']:
            print("  - Los municipios necesitan provincia_id para ser encontrados")
            print("  - Verificar que las provincias de los municipios existen")
        
        if self.incidencias_totales['reg_no_encontrado']:
            print("  - Añadir los registros faltantes a la tabla 'registros_propiedad'")

async def main():
    print("=" * 80)
    print("CARGA MASIVA DE INMATRICULACIONES CEE DESDE CSV")
    print("=" * 80)
    
    # Usar DATABASE_URL ya configurado por sipi-core
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no configurado")
        return

    # Convertir asyncpg a postgresql estándar para asyncpg raw
    dsn = DATABASE_URL
    if dsn.startswith("postgresql+asyncpg://"):
        dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")

    schema = os.getenv("DATABASE_SCHEMA", "sipi")
    print(f"Conectando a: {dsn.split('@')[-1]}")
    print(f"Usando schema: {schema}")
    
    # Definir ruta relativa del directorio output con los CSV
    # Desde el directorio del script, subir un nivel y buscar el directorio output
    csv_dir = script_dir.parent / "data" / "listado_cee" / "data" / "output"
    
    if not csv_dir.exists():
        print(f"\nERROR: No se encuentra el directorio de CSV")
        print(f"Ruta buscada: {csv_dir}")
        print("\nVerifica que la transformación del Excel se haya ejecutado")
        return
    
    # Buscar todos los archivos CSV
    csv_files = list(csv_dir.glob("*.csv"))
    
    if not csv_files:
        print(f"\nERROR: No se encontraron archivos CSV en {csv_dir}")
        print("\nPosibles causas:")
        print("  1. La transformación no se ha ejecutado")
        print("  2. Los archivos tienen otra extensión")
        print("  3. El directorio está vacío")
        return
    
    print(f"\nEncontrados {len(csv_files)} archivos CSV:")
    for csv_file in sorted(csv_files):
        size_mb = csv_file.stat().st_size / (1024*1024)
        print(f"  - {csv_file.name} ({size_mb:.2f} MB)")
    
    conn = None
    try:
        conn = await asyncpg.connect(dsn)
        
        # Establecer search_path al schema
        await conn.execute(f"SET search_path TO {schema}, public")

        loader = InmatriculacionesCEELoader(dsn, schema)
        await loader.load_caches(conn)
        
        # Contador de archivos procesados exitosamente
        archivos_exitosos = 0
        
        # Procesar cada archivo CSV en su propia transacción
        for csv_file in sorted(csv_files):
            # Saltar archivos de estadísticas si existen
            if 'estadisticas' in csv_file.name.lower() or 'resumen' in csv_file.name.lower():
                print(f"\nSaltando archivo de estadísticas: {csv_file.name}")
                continue
            
            loader.estadisticas_totales['total_archivos'] += 1
            
            try:
                async with conn.transaction():
                    exito = await loader.process_csv(conn, csv_file)
                    if exito:
                        archivos_exitosos += 1
            except Exception as e:
                print(f"\nERROR procesando {csv_file.name}: {e}")
                # Continuar con el siguiente archivo
                continue
            
        # Imprimir resumen final
        loader.print_resumen_final()
        
        print(f"\nCARGA COMPLETADA:")
        print(f"  Archivos procesados exitosamente: {archivos_exitosos}/{len(csv_files)}")
        
    except Exception as e:
        print(f"\nERROR durante la carga: {e}")
        import traceback
        traceback.print_exc()
        return
    finally:
        if conn:
            await conn.close()

if __name__ == '__main__':
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())