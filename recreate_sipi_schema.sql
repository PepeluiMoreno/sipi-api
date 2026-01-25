-- Recrear base de datos limpio para SIPI
-- Ejecutar como superusuario (postgres)

DROP DATABASE IF EXISTS sipi;
CREATE DATABASE sipi OWNER sipi;

-- Conectarse a la nueva base de datos
\c sipi

-- Solo usar schema sipi (eliminar portals temporalmente)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS sipi;