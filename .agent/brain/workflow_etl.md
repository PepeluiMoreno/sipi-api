---
description: Proceso ETL de Inmatriculaciones (Excel -> DB)
---

# ETL Inmatriculaciones

Este flujo de trabajo describe cómo procesar los datos brutos de Excel e importarlos a la base de datos de SIPI.

## 1. PREPARACIÓN (Python / Pandas)

El primer paso convierte el archivo Excel original en múltiples CSVs limpios y normalizados.

**Requisitos:**
- Archivo Excel en `sipi-api/ETL/preparation/data/input/`
- Librería `pandas` y `openpyxl` instaladas.

**Comando:**
```bash
# Desde la raíz del proyecto o ETL
python sipi-api/ETL/preparation/scripts/procesar_inmatriculaciones.py "nombre_archivo.xlsx"
```

## 2. CARGA (Loader)

El segundo paso lee los CSVs generados en `sipi-api/ETL/preparation/data/output/` y los carga en PostgreSQL.

**Acciones:**
- Crea/Busca Comunidades Autónomas, Provincias y Municipios.
- Crea/Busca Registros de la Propiedad.
- Inserta Inmuebles e Inmatriculaciones.

**Comando:**
```bash
# Ejecutar desde la raíz del workspace para que encuentre el módulo 'app'
python sipi-api/ETL/preparation/scripts/cargar_inmatriculaciones.py
```

## Notas para Migración

Si cambias de ordenador:
1. Copia la carpeta `sipi-api/ETL`.
2. Asegúrate de tener las dependencias de Python instaladas (`pip install pandas openpyxl sqlalchemy asyncpg geoalchemy2`).
3. Ejecuta el script de carga.
