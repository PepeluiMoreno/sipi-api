# alembic/env.py
from __future__ import with_statement
import os
from alembic import context
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig

# ✅ Importar Base desde tu estructura
from app.db.base import Base

config = context.config
fileConfig(config.config_file_name)

# ✅ Usar el metadata de tu Base con schema dinámico
target_metadata = Base.metadata

# ✅ Leer URL desde variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no está definida en las variables de entorno")

def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        version_table_schema=target_metadata.schema,
        include_schemas=True
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        {"sqlalchemy.url": DATABASE_URL},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=target_metadata.schema,
            include_schemas=True
        )

        with context.begin_transaction():
            # ✅ Asegurar que el schema esté activo
            if target_metadata.schema:
                context.execute(f'SET search_path TO {target_metadata.schema}')
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()