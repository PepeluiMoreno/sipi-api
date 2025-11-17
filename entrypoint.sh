#!/bin/bash
set -euo pipefail

GRAPHQL_PORT=${GRAPHQL_PORT:-8000}
DATABASE_URL=${DATABASE_URL:-}

if [[ -z "$DATABASE_URL" ]]; then
    echo "❌ ERROR: DATABASE_URL no definida" >&2
    exit 1
fi

# Garantizar que el directorio existe
[ -d alembic/versions ] || mkdir -p alembic/versions

# Aplicar migraciones idempotentemente
echo "⬆️ Aplicando migraciones..."
alembic upgrade head

echo "🚀 Iniciando GraphQL en puerto: $GRAPHQL_PORT"
exec uvicorn app.graphql.app:application \
    --host "${GRAPHQL_HOST:-0.0.0.0}" \
    --port "$GRAPHQL_PORT"
