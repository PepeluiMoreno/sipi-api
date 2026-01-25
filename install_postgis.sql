-- Script para habilitar extensión PostGIS en la base de datos sipi
-- Ejecutar como superusuario (postgres)
-- Uso: psql -U postgres -d sipi -f install_postgis.sql

-- Habilitar extensión PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

-- Verificar que la extensión está instalada
SELECT postgis_full_version();
