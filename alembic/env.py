# alembic/env.py
import os
import sys
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
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
    from app.db.base import Base
    target_metadata = Base.metadata
except Exception as e:
    print(f"❌ ERROR importando modelos: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def include_object_filter(object, name, type_, reflected, compare_to):
    """
    SOLO incluir schemas que gestionamos nosotros
    Excluir TODO lo demás (PostGIS, Tiger, sistema)
    """
    # ✅ SOLO estos schemas son nuestros
    our_schemas = {'public', 'n8n', 'auditoria'}
    
    # ✅ Tablas de sistema PostGIS en public que NO gestionamos
    postgis_system_tables = {
        'spatial_ref_sys', 'geometry_columns', 'geography_columns',
        'raster_columns', 'raster_overviews', 'topology', 'layer',
    }
    
    if type_ == "table":
        # Obtener el schema de la tabla
        table_schema = getattr(object, 'schema', None) or 'public'
        
        # ✅ Solo incluir nuestros schemas
        if table_schema not in our_schemas:
            return False
        
        # ✅ En public, excluir tablas de sistema PostGIS
        if table_schema == 'public' and name.lower() in postgis_system_tables:
            return False
    
    return True


def run_migrations_offline():
    raise RuntimeError("❌ Offline migrations no soportadas")


def run_migrations_online():
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