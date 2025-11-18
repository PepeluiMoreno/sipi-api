#!/bin/bash
# scripts/migrate.sh - Gestión de migraciones en DESARROLLO

set -euo pipefail

CMD=${1:-help}

case $CMD in
    create)
        MSG=${2:-"auto migration"}
        echo "📝 Creando nueva migración: $MSG"
        docker-compose exec graphql alembic revision --autogenerate -m "$MSG"
        ;;
    
    upgrade)
        echo "⬆️  Aplicando migraciones..."
        docker-compose exec graphql alembic upgrade head
        ;;
    
    downgrade)
        STEPS=${2:--1}
        echo "⬇️  Revirtiendo $STEPS migraciones..."
        docker-compose exec graphql alembic downgrade $STEPS
        ;;
    
    history)
        echo "📋 Historial de migraciones:"
        docker-compose exec graphql alembic history
        ;;
    
    current)
        echo "📍 Migración actual:"
        docker-compose exec graphql alembic current
        ;;
    
    reset)
        echo "🔄 RESET COMPLETO de migraciones..."
        read -p "¿Estás seguro? Esto BORRARÁ todos los datos (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose down -v
            rm -rf alembic/versions/*.py
            echo "✅ Migraciones borradas. Ahora ejecuta: ./scripts/migrate.sh init"
        fi
        ;;
    
    init)
        echo "🆕 Inicializando migraciones desde modelos..."
        docker-compose up -d db
        sleep 5
        docker-compose run --rm graphql alembic revision --autogenerate -m "Initial schema"
        docker-compose run --rm graphql alembic upgrade head
        echo "✅ Migración inicial creada"
        ;;
    
    *)
        cat <<EOF
🔧 Gestión de migraciones SIPI

Uso: ./scripts/migrate.sh [comando]

Comandos:
  create [mensaje]  - Crear nueva migración desde modelos
  upgrade          - Aplicar migraciones pendientes
  downgrade [n]    - Revertir n migraciones (default: -1)
  history          - Ver historial de migraciones
  current          - Ver migración actual
  init             - Crear migración inicial desde cero
  reset            - RESET completo (borra todo)

Ejemplos:
  ./scripts/migrate.sh create "add users table"
  ./scripts/migrate.sh upgrade
  ./scripts/migrate.sh downgrade -2
EOF
        ;;
esac