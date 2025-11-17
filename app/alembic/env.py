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

def run_migrations_offline():
    raise RuntimeError("❌ Offline migrations no soportadas")

def run_migrations_online():
    # Crear motor ASYNC
    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
        echo=False,  # Cambia a True para ver queries SQL
    )

    async def run_async_migrations():
        # Conexión async
        async with connectable.connect() as connection:
            # Ejecutar migraciones en contexto sync
            await connection.run_sync(do_run_migrations)

    def do_run_migrations(connection):
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

    # Iniciar event loop y ejecutar
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()