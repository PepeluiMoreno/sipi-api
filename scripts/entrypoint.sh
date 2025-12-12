#!/bin/bash
# entrypoint.sh - VERSIÓN MEJORADA CON AUTO-GENERACIÓN
set -e

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1 - $2"
}

log "INFO" "🚀 Iniciando SIPI GraphQL API"

# Cambiar al directorio de código
cd /code

# Verificar si existen migraciones
MIGRATION_COUNT=$(find /code/alembic/versions -name "*.py" ! -name "__*" 2>/dev/null | wc -l)

if [ "$MIGRATION_COUNT" -eq 0 ]; then
    log "WARN" "⚠️  No se encontraron migraciones en alembic/versions/"
    log "INFO" "🔨 Generando migración inicial automáticamente..."
    
    # Generar migración inicial
    if alembic revision --autogenerate -m "Migracion inicial automatica"; then
        log "INFO" "✅ Migración inicial generada exitosamente"
    else
        log "ERROR" "❌ Error generando migración inicial"
        log "WARN" "⚠️  Continuando sin aplicar migraciones..."
    fi
else
    log "INFO" "📋 Encontradas $MIGRATION_COUNT migración(es) existente(s)"
fi

# Aplicar migraciones pendientes
log "INFO" "🔄 Ejecutando migraciones de Alembic"
if alembic upgrade head; then
    log "INFO" "✅ Migraciones aplicadas correctamente"
else
    log "ERROR" "❌ Error aplicando migraciones"
    log "WARN" "⚠️  Continuando de todas formas..."
fi

# Iniciar servidor
log "INFO" "🌐 Iniciando servidor GraphQL en puerto ${GRAPHQL_PORT:-8000}"
exec uvicorn app.graphql.app:application \
    --host 0.0.0.0 \
    --port "${GRAPHQL_PORT:-8000}" \
    --reload