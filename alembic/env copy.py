# alembic/env.py
import os
import sys
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = os.getenv("DATABASE_URL")
if not database_url:
    database_url = config.get_main_option("sqlalchemy.url")

if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

try:
    from sipi.db.base import Base
    
    # ✅ DESCUBRIMIENTO AUTOMÁTICO DE MODELOS (igual que schema.py)
    import importlib
    from pathlib import Path
    
    MODELS_ROOT = os.getenv("MODELS_ROOT", "app/db/models")
    models_folder = Path(MODELS_ROOT)
    
    print(f"🔍 Descubriendo modelos en: {MODELS_ROOT}")
    
    # Importar todos los módulos en MODELS_ROOT
    models_imported = 0
    for py_file in models_folder.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        
        module_name = f"{MODELS_ROOT.replace('/', '.')}.{py_file.stem}"
        
        try:
            importlib.import_module(module_name)
            models_imported += 1
            print(f"  📦 {module_name}")
        except Exception as e:
            print(f"  ⚠️  Error importando {module_name}: {e}")
            continue
    
    print(f"✅ {models_imported} módulos importados")
    print(f"✅ {len(Base.metadata.tables)} tablas detectadas en Base.metadata")
    print(f"   Tablas: {', '.join(list(Base.metadata.tables.keys())[:5])}...")
    
    target_metadata = Base.metadata
    
except Exception as e:
    print(f"❌ ERROR importando modelos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def include_object_filter(object, name, type_, reflected, compare_to):
    """
    Solo incluir tablas que REALMENTE son nuestras.
    Excluir TODO lo demás (PostGIS, Tiger, sistema).
    """
    
    # Si es una tabla
    if type_ == "table":
        # Obtener schema
        table_schema = getattr(object, 'schema', None) or 'public'
        
        # ✅ SOLO schema public (excluir tiger, tiger_data, topology, etc)
        if table_schema != 'public':
            return False
        
        # ✅ Lista de prefijos de tablas de PostGIS/Tiger que NO tocamos
        excluded_prefixes = (
            'spatial_', 'geography_', 'geometry_', 'raster_',
            'tabblock', 'tract', 'bg', 'county', 'state',
            'place', 'zcta5', 'faces', 'edges', 'featnames',
            'addr', 'zip_', 'pagc_', 'loader_'
        )
        
        # ✅ Tablas específicas de PostGIS que NO tocamos
        excluded_tables = {
            'spatial_ref_sys', 'geometry_columns', 'geography_columns',
            'raster_columns', 'raster_overviews', 'topology', 'layer',
            'geocode_settings', 'geocode_settings_default',
            'direction_lookup', 'secondary_unit_lookup',
            'state_lookup', 'street_type_lookup', 'place_lookup',
            'county_lookup', 'countysub_lookup', 'cousub',
            'addrfeat',
        }
        
        name_lower = name.lower()
        
        # Excluir por prefijo
        if name_lower.startswith(excluded_prefixes):
            return False
        
        # Excluir por nombre exacto
        if name_lower in excluded_tables:
            return False
        
        # ✅ Solo incluir tablas que están en NUESTROS metadatos
        # Esto es lo más seguro: si no está definida en nuestros modelos, ignorarla
        if reflected and compare_to is None:
            # Es una tabla en la BD pero NO en nuestros modelos
            return False
    
    return True


def run_migrations_offline():
    raise RuntimeError("❌ Offline migrations no soportadas")


def run_migrations_online():
    # ✅ Schema personalizable via variable de entorno
    db_schema = os.getenv("DB_SCHEMA", "sipi")
    
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
        echo=False,
    )

    async def run_async_migrations():
        async with connectable.connect() as connection:
            # ✅ Crear schema si no existe
            await connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {db_schema}"))
            await connection.commit()
            
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=db_schema,  # ✅ alembic_version en schema personalizado
            include_schemas=False,
            include_object=include_object_filter,
            compare_type=True,
            compare_server_default=False,
        )
        
        # ✅ search_path: primero nuestro schema, luego public (para PostGIS)
        connection.execute(text(f"SET search_path TO {db_schema}, public"))
        
        with context.begin_transaction():
            context.run_migrations()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()