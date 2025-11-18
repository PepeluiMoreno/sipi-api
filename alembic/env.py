# alembic/env.py
import os
import sys
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Hacer que el proyecto sea importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Obtener la URL de la base de datos
database_url = os.getenv("DATABASE_URL")
if not database_url:
    database_url = config.get_main_option("sqlalchemy.url")

# Convertir postgresql:// → postgresql+asyncpg://
if database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Importar Base
try:
    from app.db.base import Base
    target_metadata = Base.metadata
except Exception as e:
    print(f"❌ ERROR importando modelos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def include_object_filter(object, name, type_, reflected, compare_to):
    """
    Excluir tablas del sistema y de PostGIS del autogenerate
    """
    # Schemas de PostGIS y sistema que NO debemos tocar
    excluded_schemas = {'tiger', 'tiger_data', 'topology', 'pg_catalog', 'information_schema'}
    
    # Prefijos de tablas de PostGIS
    postgis_prefixes = ('spatial_', 'geography_', 'geometry_', 'raster_')
    
    # Tablas específicas de PostGIS y Tiger Geocoder
    postgis_tables = {
        # PostGIS core
        'topology', 'layer',
        'spatial_ref_sys', 'geometry_columns', 'geography_columns',
        'raster_columns', 'raster_overviews',
        # Tiger geocoder
        'featnames', 'edges', 'faces', 'addr', 'addrfeat',
        'bg', 'county', 'county_lookup', 'countysub_lookup', 'cousub',
        'direction_lookup', 'geocode_settings', 'geocode_settings_default',
        'loader_lookuptables', 'loader_platform', 'loader_variables',
        'pagc_gaz', 'pagc_lex', 'pagc_rules', 'place', 'place_lookup',
        'secondary_unit_lookup', 'state', 'state_lookup', 'street_type_lookup',
        'tabblock', 'tract', 'zcta5', 'zip_lookup', 'zip_lookup_all',
        'zip_lookup_base', 'zip_state', 'zip_state_loc',
    }
    
    if type_ == "table":
        # Ignorar por schema
        if hasattr(object, 'schema') and object.schema in excluded_schemas:
            return False
        
        # Ignorar por nombre exacto
        if name.lower() in postgis_tables:
            return False
        
        # Ignorar por prefijo
        if name.lower().startswith(postgis_prefixes):
            return False
    
    return True


def run_migrations_offline():
    raise RuntimeError("❌ Offline migrations no soportadas")


def run_migrations_online():
    # Crear motor ASYNC
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
        echo=False,
    )

    async def run_async_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
        await connectable.dispose()

    def do_run_migrations(connection):
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object_filter,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()