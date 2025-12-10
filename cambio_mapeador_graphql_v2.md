# Cambio en el Mapeador GraphQL (schema.py) - Solución v2

Se ha implementado una solución más robusta para asegurar el mapeo de las **relaciones de SQLAlchemy** a los tipos GraphQL de Strawberry en `app/graphql/schema.py`.

La solución anterior (pre-registro con decorador) no fue suficiente para resolver las referencias circulares y las dependencias de tipos.

### Modificación Implementada

Se ha modificado la forma en que se crea el tipo GraphQL dinámico dentro de la función `generate_resolvers`:

1.  **Herencia Dinámica:** En lugar de usar el decorador `@mapper.type(model)` sobre la clase `DynamicType`, ahora se llama a `mapper.type(model)` para obtener una clase base que ya tiene los campos de SQLAlchemy inyectados.
2.  **Definición de Tipo:** La clase `DynamicType` ahora **hereda** de esta clase base (`BaseType`).

```python
BaseType = mapper.type(model)

@strawberry.type(name=model_name)
class DynamicType(BaseType):
    pass
```

Esta técnica asegura que los campos de columna y, crucialmente, los campos de relación (que son los que causaban problemas de resolución de tipos) se definan y resuelvan correctamente antes de que Strawberry decore la clase como un tipo GraphQL. Esto debería resolver el problema de las relaciones que no aparecen en el esquema.

El commit anterior ha sido revertido para aplicar esta nueva solución.


