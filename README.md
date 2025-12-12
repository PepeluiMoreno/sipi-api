# SIPI-API

**Sistema de Información del Patrimonio Inmatriculado - API GraphQL**

API GraphQL desarrollada en Python para la gestión integral del patrimonio inmatriculado, con soporte geoespacial y generación automática de esquemas desde modelos SQLAlchemy.

## 📋 Tabla de Contenidos

- [Arquitectura](#arquitectura)
- [Stack Tecnológico](#stack-tecnológico)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Modelos de Datos](#modelos-de-datos)
- [Generación Automática de GraphQL](#generación-automática-de-graphql)
- [Instalación y Configuración](#instalación-y-configuración)
- [Uso](#uso)
- [Endpoints](#endpoints)
- [Base de Datos](#base-de-datos)
- [Desarrollo](#desarrollo)

## 🏗️ Arquitectura

SIPI-API sigue una arquitectura modular basada en:

- **API GraphQL**: Servidor ASGI con Strawberry GraphQL
- **ORM Asíncrono**: SQLAlchemy 2.0 con soporte async/await
- **Base de Datos**: PostgreSQL con extensión PostGIS para datos geoespaciales
- **Generación Automática**: Schema GraphQL generado dinámicamente desde modelos SQLAlchemy
- **Contenedores**: Docker Compose para orquestación de servicios

### Flujo de Datos

```
Cliente GraphQL → Starlette ASGI → Strawberry GraphQL → SQLAlchemy Async → PostgreSQL/PostGIS
```

## 🛠️ Stack Tecnológico

### Core

- **Python 3.11**
- **Strawberry GraphQL 0.243.0**: Framework GraphQL moderno con soporte ASGI
- **SQLAlchemy 2.0.36**: ORM con soporte asíncrono completo
- **Starlette 0.41.3**: Framework ASGI ligero
- **Uvicorn**: Servidor ASGI de alto rendimiento

### Base de Datos

- **PostgreSQL**: Base de datos relacional
- **PostGIS**: Extensión geoespacial (Geometry/Geography)
- **Alembic 1.14.0**: Migraciones de esquema
- **asyncpg 0.30.0**: Driver asíncrono para PostgreSQL

### Utilidades

- **GeoAlchemy2 0.15.2**: Integración SQLAlchemy-PostGIS
- **Pydantic 2.9.2**: Validación de datos y configuración
- **Pandas 2.2.0**: Procesamiento de datos (ETL)
- **Shapely 2.1.2**: Operaciones geométricas
- **OSMnx 2.0.7**: Integración con OpenStreetMap

## 📁 Estructura del Proyecto

```
sipi-api/
├── app/
│   ├── core/              # Configuración central
│   │   └── config.py      # Settings y variables de entorno
│   ├── db/
│   │   ├── base.py        # Base declarativa SQLAlchemy
│   │   ├── models/        # Modelos de dominio
│   │   │   ├── inmuebles.py
│   │   │   ├── actores.py
│   │   │   ├── geografia.py
│   │   │   ├── actuaciones.py
│   │   │   ├── transmisiones.py
│   │   │   └── ...
│   │   ├── mixins/        # Mixins reutilizables
│   │   │   ├── base.py    # UUIDPKMixin, AuditMixin
│   │   │   ├── identificacion.py
│   │   │   ├── contacto.py
│   │   │   └── ...
│   │   └── sessions/      # Factories de sesión
│   │       ├── async_session.py
│   │       └── sync_session.py
│   └── graphql/
│       ├── app.py         # Aplicación Starlette principal
│       ├── schema.py      # Generación automática de schema
│       ├── mapper.py      # Mapeador SQLAlchemy → Strawberry
│       ├── mapper/        # Sistema de mapeo avanzado
│       │   ├── enhanced_mapper.py
│       │   ├── property_extractor.py
│       │   ├── type_builder.py
│       │   └── cache.py
│       ├── types.py       # Tipos GraphQL personalizados
│       ├── crud.py        # Operaciones CRUD
│       └── custom_fields.py
├── alembic/               # Migraciones de base de datos
├── scripts/               # Scripts de utilidad
│   ├── entrypoint.sh     # Script de inicio del contenedor
│   ├── wait-for-db.sh    # Espera a PostgreSQL
│   └── ...
├── ETL/                   # Procesos ETL
├── docker-compose.yml     # Orquestación de servicios
├── Dockerfile             # Imagen de la aplicación
├── requirements.txt       # Dependencias Python
└── alembic.ini            # Configuración Alembic
```

## 🗄️ Modelos de Datos

### Modelos Principales

#### Inmueble
Entidad central del sistema. Representa un bien inmueble del patrimonio.

**Campos destacados:**
- Identificación: `nombre`, `descripcion`
- Geografía: `comunidad_autonoma_id`, `provincia_id`, `municipio_id`, `direccion`
- Coordenadas: `coordenadas` (Geometry POINT, SRID 4326)
- Clasificación: `tipo_inmueble_id`, `figura_proteccion_id`
- Estados: `estado_conservacion_id`, `estado_tratamiento_id`
- Superficies: `superficie_construida`, `superficie_parcela`
- Valores: `valor_catastral`, `valor_mercado`

**Relaciones:**
- `denominaciones`: Múltiples denominaciones históricas
- `inmatriculaciones`: Registros de propiedad
- `documentos`: Documentos asociados
- `actuaciones`: Intervenciones realizadas
- `transmisiones`: Transferencias de propiedad
- `osm_ext`: Datos de OpenStreetMap
- `wd_ext`: Datos de Wikidata

#### Actores
Personas físicas y jurídicas que intervienen en el dominio.

**Tipos:**
- `Adquiriente`: Comprador en transmisiones
- `Transmitente`: Vendedor en transmisiones
- `Tecnico`: Profesionales (arquitectos, ingenieros)
- `Administracion`: Administraciones públicas
- `Notaria`: Notarías
- `RegistroPropiedad`: Registros de propiedad
- `ColegioProfesional`: Colegios profesionales
- `AgenciaInmobiliaria`: Agencias inmobiliarias
- `Diocesis`: Diócesis eclesiásticas

**Mixins aplicados:**
- `IdentificacionMixin`: DNI/NIE/NIF/CIF, nombre, apellidos
- `ContactoDireccionMixin`: Email, teléfono, dirección postal
- `TitularidadMixin`: Información de titularidad

#### Geografía
Estructura administrativa española.

- `ComunidadAutonoma`: 17 comunidades autónomas
- `Provincia`: 50 provincias españolas
- `Municipio`: ~8.000 municipios

#### Actuaciones
Intervenciones realizadas sobre inmuebles.

- `Actuacion`: Intervención principal
- `ActuacionTecnico`: Técnicos involucrados
- `ActuacionSubvencion`: Subvenciones asociadas

#### Transmisiones
Transferencias de propiedad.

- `Transmision`: Transmisión principal
- `TransmisionAnunciante`: Anunciantes en transmisiones

#### Otros Modelos

- `FiguraProteccion`: Figuras de protección (BIC, etc.)
- `Documento`: Documentos del sistema
- `SubvencionAdministracion`: Subvenciones públicas
- `FuenteHistoriografica`: Fuentes históricas

### Mixins del Sistema

#### UUIDPKMixin
Proporciona clave primaria UUID estándar:
```python
id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
```

#### AuditMixin
Sistema completo de auditoría:
- `created_at`, `updated_at`, `deleted_at`: Timestamps UTC
- `created_by_id`, `updated_by_id`, `deleted_by_id`: Usuarios responsables
- `created_from_ip`, `updated_from_ip`: IPs de origen
- `soft_delete()`: Eliminación lógica
- `restore()`: Restauración de registros eliminados

#### IdentificacionMixin
Identificación unificada para personas:
- `tipo_identificacion`: Enum (DNI, NIE, NIF, CIF, etc.)
- `identificacion`: Número de identificación
- `nombre`, `apellidos`: Nombre completo
- `nombre_completo`: Propiedad calculada

#### ContactoDireccionMixin
Información de contacto y dirección:
- Email, teléfono, fax
- Dirección postal completa
- Relación con `Municipio`

#### TitularidadMixin
Información de titularidad para entidades.

## 🔄 Generación Automática de GraphQL

El sistema genera automáticamente el schema GraphQL completo desde los modelos SQLAlchemy mediante el módulo `app/graphql/schema.py`.

### Proceso de Generación

1. **Carga de Modelos** (`load_all_models`)
   - Escanea `app/db/models/`
   - Importa dinámicamente todos los modelos
   - Deduplica por nombre de clase

2. **Creación de Tipos GraphQL** (`create_graphql_types`)
   - Mapea columnas SQLAlchemy → tipos GraphQL
   - Detecta propiedades `@property` y las incluye
   - Maneja tipos especiales (Geometry, Decimal, DateTime)
   - Excluye campos geoespaciales complejos del schema

3. **Creación de Input Types** (`create_input_types`)
   - `{Modelo}CreateInput`: Campos para creación (sin ID)
   - `{Modelo}UpdateInput`: Campos para actualización (todos opcionales, con ID)

4. **Generación de Queries** (`create_queries`)
   - `get{Modelo}(id: ID!)`: Obtener por ID
   - `list{Modelo}s(limit: Int)`: Listar todos (limitado)
   - `search{Modelo}s(search: String, limit: Int)`: Búsqueda por texto

5. **Generación de Mutations** (`create_mutations`)
   - `create{Modelo}(data: {Modelo}CreateInput!)`: Crear registro
   - `delete{Modelo}(id: ID!)`: Eliminar registro

### Mapeo de Tipos

| Python/SQLAlchemy | GraphQL |
|-------------------|---------|
| `int` (id) | `ID!` |
| `int` | `Int` / `Int!` |
| `str` | `String` / `String!` |
| `bool` | `Boolean` / `Boolean!` |
| `float` | `Float` / `Float!` |
| `Decimal` | `Float` / `Float!` |
| `datetime` | `String` (ISO 8601) |
| `date` | `String` (ISO 8601) |
| `Geometry` | Excluido del schema |

### Características Avanzadas

- **Propiedades Calculadas**: Las propiedades `@property` se detectan automáticamente y se incluyen en el schema
- **Lazy Loading**: El schema se crea bajo demanda (lazy initialization) con locks para thread-safety
- **Cache de Tipos**: Sistema de caché para evitar regeneración innecesaria
- **Manejo de Errores**: Logging detallado de modelos que fallan en la generación

## 🚀 Instalación y Configuración

### Requisitos Previos

- Docker y Docker Compose
- Python 3.11+ (para desarrollo local)

### Instalación con Docker

1. **Clonar el repositorio**
```bash
git clone <repository-url>
cd sipi-api
```

2. **Configurar variables de entorno**
Crear archivo `.env`:
```env
# Base de datos
DATABASE_URL=postgresql+asyncpg://sipi:sipi@db:5432/sipi
POSTGRES_USER=sipi
POSTGRES_PASSWORD=sipi
POSTGRES_DB=sipi
POSTGRES_PORT=5432

# GraphQL
GRAPHQL_HOST=0.0.0.0
GRAPHQL_PORT=8040

# Entorno
ENV=development
LOG_LEVEL=INFO

# SQLAlchemy
SQLALCHEMY_ECHO=false
POOL_SIZE=20
POOL_MAX_OVERFLOW=10
POOL_TIMEOUT=30
POOL_RECYCLE=3600

# Schema de base de datos
DB_SCHEMA=sipi
```

3. **Construir e iniciar servicios**
```bash
docker-compose up -d --build
```

4. **Verificar estado**
```bash
docker-compose ps
docker-compose logs -f graphql
```

### Instalación Local (Desarrollo)

1. **Crear entorno virtual**
```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

2. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

3. **Configurar base de datos PostgreSQL**
- Instalar PostgreSQL con PostGIS
- Crear base de datos:
```sql
CREATE DATABASE sipi;
CREATE EXTENSION postgis;
```

4. **Configurar variables de entorno**
```bash
export DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/sipi"
export DB_SCHEMA="sipi"
```

5. **Ejecutar migraciones**
```bash
alembic upgrade head
```

6. **Iniciar servidor**
```bash
uvicorn app.graphql.app:application --host 0.0.0.0 --port 8040 --reload
```

## 📖 Uso

### Acceso a GraphiQL

Una vez iniciado el servicio, acceder a:
```
http://localhost:8040/graphql
```

### Ejemplo de Query

```graphql
query {
  listInmuebles(limit: 10) {
    id
    nombre
    descripcion
    superficieConstruida
    valorCatastral
    municipio {
      nombre
      provincia {
        nombre
        comunidadAutonoma {
          nombre
        }
      }
    }
  }
}
```

### Ejemplo de Mutation

```graphql
mutation {
  createInmueble(data: {
    nombre: "Iglesia de San Juan"
    descripcion: "Iglesia del siglo XV"
    superficieConstruida: 500.50
  }) {
    id
    nombre
    createdAt
  }
}
```

### Ejemplo de Búsqueda

```graphql
query {
  searchInmuebles(search: "iglesia", limit: 20) {
    id
    nombre
    descripcion
  }
}
```

## 🌐 Endpoints

### GraphQL

- **POST `/graphql`**: Endpoint principal GraphQL
- **GET `/graphql`**: GraphiQL (interfaz interactiva)

### Utilidades

- **GET `/`**: Página de documentación con enlaces
- **GET `/health`**: Health check del servicio
  ```json
  {
    "status": "ok",
    "service": "graphql"
  }
  ```
- **GET `/schema.graphql`**: Schema GraphQL en formato SDL
- **GET `/stats`**: Estadísticas del schema
  ```json
  {
    "status": "ok",
    "types": 45,
    "queries": 135,
    "mutations": 90
  }
  ```

## 🗃️ Base de Datos

### Configuración

- **Motor**: PostgreSQL 14+
- **Extensión**: PostGIS 3.0+
- **Schema**: Configurable via `DB_SCHEMA` (default: `sipi`)
- **Pool de Conexiones**: AsyncAdaptedQueuePool
  - Tamaño: 20 conexiones
  - Overflow: 10 conexiones adicionales
  - Timeout: 30 segundos
  - Recycle: 3600 segundos

### Migraciones

El sistema usa **Alembic** para gestionar migraciones:

```bash
# Crear nueva migración
alembic revision --autogenerate -m "Descripción del cambio"

# Aplicar migraciones
alembic upgrade head

# Revertir migración
alembic downgrade -1
```

**Nota**: El script `entrypoint.sh` genera automáticamente una migración inicial si no existen migraciones.

### Datos Geoespaciales

- **SRID**: 4326 (WGS84)
- **Tipos soportados**: POINT, POLYGON, LINESTRING
- **Campos**: `coordenadas` en modelo `Inmueble`
- **Operaciones**: Consultas espaciales mediante PostGIS

### Índices

El sistema crea índices automáticamente para:
- Claves primarias (UUID)
- Claves foráneas
- Campos de auditoría (`created_at`, `updated_at`, `deleted_at`)
- Campos de búsqueda frecuente (`nombre`, `activo`)
- Campos geoespaciales (mediante PostGIS)

## 🔧 Desarrollo

### Estructura de Modelos

Al crear un nuevo modelo:

```python
from app.db.base import Base
from app.db.mixins import UUIDPKMixin, AuditMixin

class MiModelo(UUIDPKMixin, AuditMixin, Base):
    __tablename__ = "mi_tabla"
    
    nombre: Mapped[str] = mapped_column(String(255), index=True)
    # ... más campos
```

El modelo se detectará automáticamente y se generarán:
- Tipo GraphQL `MiModelo`
- Input types `MiModeloCreateInput` y `MiModeloUpdateInput`
- Queries: `getMiModelo`, `listMiModelos`, `searchMiModelos`
- Mutations: `createMiModelo`, `deleteMiModelo`

### Agregar Propiedades Calculadas

```python
class Inmueble(Base):
    # ... campos ...
    
    @property
    def superficie_total(self) -> float:
        """Superficie total (construida + parcela)"""
        construida = self.superficie_construida or 0
        parcela = self.superficie_parcela or 0
        return float(construida + parcela)
```

La propiedad `superficieTotal` aparecerá automáticamente en el schema GraphQL.

### Logging

El sistema usa el módulo `logging` de Python:

```python
import logging
logger = logging.getLogger('app.graphql')
logger.info("Mensaje informativo")
logger.error("Error", exc_info=True)
```

### Testing

```bash
# Ejecutar tests (cuando estén implementados)
pytest tests/
```

### Scripts Útiles

- `scripts/entrypoint.sh`: Script de inicio del contenedor
- `scripts/wait-for-db.sh`: Espera a que PostgreSQL esté listo
- `scripts/export_schema.py`: Exporta el schema GraphQL

## 📝 Notas Técnicas

### Thread Safety

El schema GraphQL se crea con locks (`threading.Lock`) para garantizar thread-safety en entornos multi-threaded.

### Lazy Initialization

El schema se crea bajo demanda (lazy) para:
- Reducir tiempo de inicio
- Permitir importaciones circulares
- Manejar errores de forma más controlada

### Manejo de Sesiones

Las sesiones de base de datos se inyectan en el contexto de la request:

```python
scope["state"]["db"] = async_session_maker()
```

Se cierran automáticamente al finalizar la request.

### Soft Delete

Todos los modelos con `AuditMixin` soportan eliminación lógica:

```python
instance.soft_delete(user_id="...")
instance.restore()
```

Las queries automáticas pueden filtrar registros eliminados si se implementa.

## 📄 Licencia

[Especificar licencia]

## 👥 Contribuidores

[Especificar contribuidores]

---

**Versión**: 1.0.0  
**Última actualización**: 2025

