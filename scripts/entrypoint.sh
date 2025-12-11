#!/bin/bash
# entrypoint.sh - VERSIÓN MÍNIMA
set -e

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1 - $2"
}

log "INFO" "Iniciando SIPI GraphQL API"

# Solo ejecutar migraciones y arrancar
cd /code
log "INFO" "Ejecutando migraciones de Alembic"
alembic upgrade head

log "INFO" "Iniciando servidor GraphQL en puerto ${GRAPHQL_PORT:-8000}"
exec uvicorn app.graphql.app:application \
    --host 0.0.0.0 \
    --port "${GRAPHQL_PORT:-8000}" \
    --reload