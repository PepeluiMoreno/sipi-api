# Problema con Alembic Autogenerate y Schemas Personalizados

## Problema Identificado

Alembic detecta correctamente las diferencias entre los metadatos y la base de datos (48 tablas que faltan), pero **no genera código** en las migraciones cuando se usa `--autogenerate` con schemas personalizados en PostgreSQL.

## Diagnóstico

1. **Alembic detecta las diferencias**: Al ejecutar `alembic revision --autogenerate`, Alembic encuentra correctamente que faltan 48 tablas en el schema `sipi`.

2. **No genera código**: A pesar de detectar las diferencias, las migraciones generadas están vacías (solo contienen `pass`).

3. **El problema NO está en el filtro**: Se probó con y sin `include_object_filter`, y el problema persiste.

4. **El problema NO está en `include_schemas`**: Se probó con `include_schemas=[db_schema]`, `include_schemas=True`, y `include_schemas=None`, sin resultados.

## Posibles Causas

Este parece ser un **bug conocido de Alembic** cuando se trabaja con:
- Schemas personalizados en PostgreSQL
- Tablas con nombres que incluyen el schema (`sipi.tablename`)
- Comparación de metadatos reflejados vs target_metadata con schemas personalizados

## Solución Temporal Implementada

Se creó una **migración inicial manual** (`6ce5012d6481_migración_inicial.py`) que:

1. Crea los enums necesarios (`nivel_proteccion`, `tipoidentificacion`)
2. Usa `Base.metadata.create_all()` para crear todas las tablas usando el ORM

Esta solución cumple con el requisito de usar el ORM y no SQL directo.

## Configuración Actual

- `include_schemas=[db_schema]`: Solo compara nuestro schema
- `include_object_filter`: Filtro mejorado para incluir tablas de nuestro schema
- `version_table_schema=db_schema`: Tabla `alembic_version` en nuestro schema

## Recomendaciones para Futuras Migraciones

Para cambios futuros en los modelos:

1. **Probar autogenerate primero**: 
   ```bash
   alembic revision --autogenerate -m "Descripción del cambio"
   ```

2. **Si la migración está vacía pero hay cambios**:
   - Verificar que los modelos estén correctamente importados
   - Verificar que los cambios estén en los modelos SQLAlchemy
   - Considerar crear la migración manualmente usando `op.create_table()` o `op.add_column()`

3. **Alternativa**: Usar `Base.metadata.create_all()` dentro de funciones de migración para cambios complejos

## Referencias

- Alembic 1.14.1
- SQLAlchemy 2.0.36
- PostgreSQL con PostGIS
- Schema personalizado: `sipi`

## Estado

- ✅ Migración inicial creada y aplicada
- ✅ 51 tablas creadas correctamente
- ⚠️ Autogenerate no funciona para migración inicial
- ❓ Pendiente probar autogenerate para cambios incrementales

