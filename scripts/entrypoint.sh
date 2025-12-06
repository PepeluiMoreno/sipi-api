#!/bin/bash
set -e

DATABASE_URL=${DATABASE_URL:-}
GRAPHQL_PORT=${GRAPHQL_PORT:-8000}

if [[ -z "$DATABASE_URL" ]]; then
    echo "❌ ERROR: DATABASE_URL no definida"
    exit 1
fi

# ✅ Esperar a PostgreSQL con retry
echo "⏳ Esperando a PostgreSQL..."
max_retries=30
retry=0

while [ $retry -lt $max_retries ]; do
    if python -c "
import sys
try:
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    
    async def check():
        try:
            engine = create_async_engine('$DATABASE_URL', pool_pre_ping=True)
            async with engine.connect() as conn:
                await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
            await engine.dispose()
            return True
        except:
            return False
    
    sys.exit(0 if asyncio.run(check()) else 1)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
        echo "✅ PostgreSQL listo"
        break
    fi
    
    retry=$((retry + 1))
    echo "⏳ Intento $retry/$max_retries..."
    sleep 2
done

if [ $retry -eq $max_retries ]; then
    echo "❌ Timeout esperando PostgreSQL"
    exit 1
fi

# Verificar si hay tablas en la base de datos
echo "🔍 Verificando estado de la base de datos..."
has_tables=$(python -c "
import sys
try:
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine
    
    async def check_tables():
        try:
            engine = create_async_engine('$DATABASE_URL')
            async with engine.connect() as conn:
                result = await conn.execute(__import__('sqlalchemy').text(
                    \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE'\"
                ))
                count = result.scalar()
            await engine.dispose()
            return count > 0
        except:
            return False
    
    sys.exit(0 if asyncio.run(check_tables()) else 1)
except Exception as e:
    sys.exit(1)
" 2>/dev/null && echo "1" || echo "0")

# Si no hay tablas, crear migración inicial
if [ "$has_tables" = "0" ]; then
    echo "📝 Base de datos vacía. Creando migración inicial..."
    
    # Limpiar migraciones antiguas si existen
    rm -f /code/alembic/versions/*.py
    
    # Crear migración inicial
    cd /code
    alembic revision --autogenerate -m "Initial schema"
else
    echo "✅ La base de datos ya tiene tablas"
fi

# Aplicar migraciones pendientes
echo "⬆️  Aplicando migraciones..."
cd /code
alembic upgrade head

# Arrancar API
echo "🚀 Iniciando API en puerto $GRAPHQL_PORT..."
exec uvicorn app.graphql.app:application \
    --host 0.0.0.0 \
    --port "$GRAPHQL_PORT" \
    --reload