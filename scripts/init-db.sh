#!/bin/bash
# scripts/init-db.sh
# Script ejecutado automáticamente al crear la BD por primera vez
# Se ejecuta en /docker-entrypoint-initdb.d/

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 SIPI - Inicializando Base de Datos PostgreSQL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Usuario: $POSTGRES_USER"
echo "📊 Base de datos: $POSTGRES_DB"
echo ""

# Ejecutar SQL de inicialización
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- =================================================================
    -- EXTENSIONES POSTGRESQL
    -- =================================================================
    
    \echo '📦 Instalando extensiones...'
    
    -- Criptografía (para UUIDs y hashing)
    CREATE EXTENSION IF NOT EXISTS pgcrypto;
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    
    -- Geoespacial (PostGIS completo)
    CREATE EXTENSION IF NOT EXISTS postgis;
    CREATE EXTENSION IF NOT EXISTS postgis_topology;
    CREATE EXTENSION IF NOT EXISTS postgis_raster;
    
    -- Utilidades adicionales
    CREATE EXTENSION IF NOT EXISTS btree_gist;        -- Índices avanzados
    CREATE EXTENSION IF NOT EXISTS pg_stat_statements; -- Estadísticas de queries
    CREATE EXTENSION IF NOT EXISTS pg_trgm;           -- Búsqueda de texto difusa
    CREATE EXTENSION IF NOT EXISTS unaccent;          -- Eliminar acentos
    
    \echo '✅ Extensiones instaladas'
    \echo ''
    
    -- =================================================================
    -- SCHEMAS
    -- =================================================================
    
    \echo '🗂️  Creando schemas...'
    
    -- Schema para n8n (automatización)
    CREATE SCHEMA IF NOT EXISTS n8n;
    
    -- Schema para auditoría (opcional)
    CREATE SCHEMA IF NOT EXISTS auditoria;
    
    \echo '✅ Schemas creados'
    \echo ''
    
    -- =================================================================
    -- FUNCIONES ÚTILES
    -- =================================================================
    
    \echo '⚙️  Creando funciones útiles...'
    
    -- Función para actualizar updated_at automáticamente
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS \$\$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    \$\$ language 'plpgsql';
    
    -- Función para generar UUIDs v4
    CREATE OR REPLACE FUNCTION generate_uuid() 
    RETURNS UUID AS \$\$
    BEGIN
        RETURN gen_random_uuid();
    END;
    \$\$ LANGUAGE plpgsql;
    
    \echo '✅ Funciones creadas'
    \echo ''
    
    -- =================================================================
    -- PERMISOS
    -- =================================================================
    
    \echo '🔐 Configurando permisos...'
    
    GRANT ALL PRIVILEGES ON SCHEMA n8n TO ${POSTGRES_USER};
    GRANT ALL PRIVILEGES ON SCHEMA auditoria TO ${POSTGRES_USER};
    GRANT ALL PRIVILEGES ON SCHEMA public TO ${POSTGRES_USER};
    
    \echo '✅ Permisos configurados'
    \echo ''
    
    -- =================================================================
    -- CONFIGURACIÓN
    -- =================================================================
    
    \echo '⚙️  Aplicando configuración...'
    
    -- Zona horaria
    ALTER DATABASE ${POSTGRES_DB} SET timezone TO 'Europe/Madrid';
    
    \echo '✅ Configuración aplicada'
    \echo ''
    
    -- =================================================================
    -- VERIFICACIÓN
    -- =================================================================
    
    \echo '🔍 Verificando instalación...'
    \echo ''
    
    -- Listar extensiones instaladas
    \echo '📦 Extensiones instaladas:'
    SELECT 
        extname AS "Extensión", 
        extversion AS "Versión"
    FROM pg_extension 
    WHERE extname NOT IN ('plpgsql')
    ORDER BY extname;
    
    \echo ''
    \echo '🗂️  Schemas disponibles:'
    SELECT schema_name AS "Schema" 
    FROM information_schema.schemata 
    WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
    ORDER BY schema_name;
    
    \echo ''
    \echo '⚙️  Configuración de zona horaria:'
    SHOW timezone;
    
EOSQL

# Resultado final
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Base de datos inicializada correctamente"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Siguiente paso: Aplicar migraciones de Alembic"
echo "   → docker-compose run --rm graphql alembic upgrade head"
echo ""