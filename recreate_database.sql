-- Borrar completamente y recrear base de datos
-- Ejecutar como superusuario (postgres)

DROP DATABASE IF EXISTS sipi;
CREATE DATABASE sipi OWNER sipi;

-- Conectarse a la nueva base de datos
\c sipi

-- Crear extensión y esquemas
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE SCHEMA IF NOT EXISTS sipi;
CREATE SCHEMA IF NOT EXISTS portals;