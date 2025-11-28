# Propuesta de Migración: Generador de GraphQL a `strawberry-sqlalchemy-mapper`

## Introducción

Este documento justifica la migración del generador de tipos GraphQL personalizado (implementado en `app/graphql/mapper/enhanced_mapper.py`) a la librería estándar de la comunidad **`strawberry-sqlalchemy-mapper`**. La migración se ha implementado en la rama `feat/strawberry-sqlalchemy` para su revisión.

El objetivo es reducir la deuda técnica, aumentar la robustez del esquema y simplificar el mantenimiento, manteniendo la funcionalidad de generación automática de tipos y operaciones CRUD.

## 1. Justificación del Cambio: Deuda Técnica y Fragilidad

La implementación actual es un generador de esquema a medida que **recrea la funcionalidad** de una librería existente. Esto introduce dos problemas principales:

1.  **Fragilidad en la Inferencia de Tipos:** La lógica personalizada para inferir tipos de propiedades y métodos en los modelos de SQLAlchemy es propensa a errores.
2.  **Mantenimiento:** El equipo de desarrollo es responsable de mantener el mapeador, en lugar de apoyarse en la comunidad de código abierto.

## 2. Comparación de Código: Antes y Después

El cambio se centra en eliminar el código personalizado y adaptar el archivo principal `schema.py` para usar la librería estándar.

### A. Eliminación del Mapeador Personalizado

Se elimina el directorio completo `app/graphql/mapper/` (incluyendo `enhanced_mapper.py`, `SQLAlchemyMapper.py`, etc.).

| Código Anterior (en `enhanced_mapper.py`) | Código Nuevo |
| :--- | :--- |
| **Lógica de Mapeo de Tipos (150+ líneas):** <br> Incluye funciones como `_infer_return_type` que usan heurísticas (e.g., nombres de métodos) para adivinar el tipo de retorno de una propiedad. | **Ninguno.** La librería `strawberry-sqlalchemy-mapper` se encarga de esta lógica de forma robusta, basándose en los metadatos de SQLAlchemy y los *type-hints* de Python. |

**Ejemplo de Fragilidad (Código Anterior):**

```python
# Extracto de enhanced_mapper.py, línea 153
# Lógica de inferencia basada en el nombre
if name.startswith(('is_', 'has_', 'tiene_', 'esta_')):
    return bool
```
> **Problema:** Si una propiedad se llama `get_is_active`, esta lógica falla. La librería estándar utiliza la introspección de SQLAlchemy, que es mucho más fiable.

### B. Adaptación de `app/graphql/schema.py`

El archivo principal solo necesita cambiar la importación y la instanciación del mapeador.

| Código Anterior (Rama `main`) | Código Nuevo (Rama `feat/strawberry-sqlalchemy`) |
| :--- | :--- |
| ```python
# app/graphql/schema.py
from app.graphql.mapper.enhanced_mapper import EnhancedSQLAlchemyMapper
from app.graphql.mapper import SQLAlchemyMapper # Tu clase local
 
# ...
# Instanciación de tu clase local
mapper = SQLAlchemyMapper()
``` | ```python
# app/graphql/schema.py
from strawberry_sqlalchemy_mapper import SQLAlchemyMapper as StrawberrySQLAlchemyMapper
# from app.graphql.mapper import SQLAlchemyMapper # Eliminado
 
# ...
# Instanciación de la clase de la librería
mapper = StrawberrySQLAlchemyMapper()
``` |

## 3. Funcionalidad Asegurada y Mejorada

La migración **mantiene** la funcionalidad de generación de CRUD y **mejora** el mapeo de tipos y relaciones.

| Funcionalidad | Estado en `main` | Estado en `feat/strawberry-sqlalchemy` |
| :--- | :--- | :--- |
| **Generación de Tipos** | Funcional, pero frágil. | **Funcional y Robusta.** |
| **Generación de Inputs (Create/Update)** | Funcional. | **Funcional y Estándar.** Se usa `partial=True` para `Update` en lugar de la lógica personalizada. |
| **Generación de Queries/Mutations CRUD** | Funcional (gestionado por `CRUDResolver`). | **Funcional.** El `CRUDResolver` no necesita cambios, ya que solo requiere el tipo generado por el mapeador. |
| **Manejo de Relaciones** | Manual o requiere lógica adicional. | **Automático.** La librería mapea automáticamente las relaciones de SQLAlchemy. |

### Ejemplo de Mejora: Mapeo de Relaciones

Con la librería estándar, si tu modelo `Actuacion` tiene una relación `documentos = relationship("Documento")`, el tipo GraphQL generado para `Actuacion` incluirá automáticamente un campo `documentos` que resuelve a una lista de tipos `Documento`.

**Esto elimina la necesidad de escribir *resolvers* manuales para la navegación de datos en el esquema.**

## Conclusión

La migración a **`strawberry-sqlalchemy-mapper`** es un paso crucial para la madurez del proyecto. Elimina código personalizado complejo y lo reemplaza con una solución estándar de la comunidad, lo que resulta en un esquema de GraphQL más robusto, fácil de mantener y con mejor soporte para las características avanzadas de SQLAlchemy, como el mapeo automático de relaciones.

Se recomienda fusionar la rama `feat/strawberry-sqlalchemy` después de una revisión exitosa.

---
*Análisis generado por Manus AI.*
