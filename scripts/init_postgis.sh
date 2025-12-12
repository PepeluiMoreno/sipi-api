#!/bin/bash
# Script para inicializar PostgreSQL con PostGIS y schema sipi

set -e

echo "🔧 Inicializando PostgreSQL con PostGIS y schema sipi"
echo "======================================================"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 1. Recrear extensiones PostGIS en schema public
echo ""
echo "📦 Paso 1: Recreando extensiones PostGIS..."
docker exec sipi-db psql -U sipi -d sipi << 'EOF'
-- Recrear extensiones PostGIS si no existen
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
CREATE EXTENSION IF NOT EXISTS fuzzystrmatch;
CREATE EXTENSION IF NOT EXISTS postgis_tiger_geocoder;

-- Verificar
SELECT postgis_full_version();
EOF

echo -e "${GREEN}✅ Extensiones PostGIS creadas${NC}"

# 2. Crear schema sipi
echo ""
echo "📁 Paso 2: Creando schema sipi..."
docker exec sipi-db psql -U sipi -d sipi << 'EOF'
-- Crear schema sipi si no existe
CREATE SCHEMA IF NOT EXISTS sipi;

-- Dar permisos
GRANT ALL ON SCHEMA sipi TO sipi;
GRANT ALL ON ALL TABLES IN SCHEMA sipi TO sipi;
GRANT ALL ON ALL SEQUENCES IN SCHEMA sipi TO sipi;

-- Establecer search_path por defecto
ALTER DATABASE sipi SET search_path TO sipi, public;
EOF

echo -e "${GREEN}✅ Schema sipi creado${NC}"

# 3. Verificar configuración
echo ""
echo "🔍 Paso 3: Verificando configuración..."
docker exec sipi-db psql -U sipi -d sipi << 'EOF'
-- Ver schemas
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name IN ('public', 'sipi')
ORDER BY schema_name;

-- Ver extensiones
SELECT extname, extversion 
FROM pg_extension 
WHERE extname LIKE 'postgis%';

-- Ver search_path
SHOW search_path;
EOF

echo ""
echo -e "${GREEN}✅ Inicialización completada${NC}"
echo ""
echo "📋 Resumen:"
echo "  - Schema 'public': PostGIS y extensiones"
echo "  - Schema 'sipi': Tablas de la aplicación"
echo "  - search_path: sipi, public"
echo ""
echo "Ahora puedes ejecutar las migraciones con:"
echo "  docker-compose restart graphql"