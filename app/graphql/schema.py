# app/graphql/schema.py - VERSIÓN COMPLETA CORREGIDA
import strawberry
import logging
from typing import List, Optional, Dict, Any, Type
from pathlib import Path
import importlib
import inspect
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, select, or_
from sqlalchemy.orm import RelationshipProperty

logger = logging.getLogger(__name__)

def get_graphql_type_for_column(column):
    """Determina el tipo GraphQL para una columna SQLAlchemy"""
    field_name = column.name
    
    try:
        python_type = column.type.python_type
        
        if python_type == int:
            if field_name == 'id':
                return strawberry.ID
            else:
                return Optional[int] if column.nullable else int
        elif python_type == str:
            return Optional[str] if column.nullable else str
        elif python_type == bool:
            return Optional[bool] if column.nullable else bool
        elif python_type == float:
            return Optional[float] if column.nullable else float
        elif python_type == datetime:
            return Optional[str] if column.nullable else str
        elif python_type == date:
            return Optional[str] if column.nullable else str
        elif python_type == Decimal:
            return Optional[float] if column.nullable else float
        else:
            return Optional[str] if column.nullable else str
            
    except NotImplementedError:
        # Manejar tipos especiales (geometry, json, etc.)
        return Optional[str] if column.nullable else str

def load_all_models(folder: str = "app/db/models"):
    """Carga todos los modelos SQLAlchemy sin duplicados"""
    models_dict = {}  # Usar dict para deduplicar por nombre
    folder_path = Path(folder)
    
    for py_file in folder_path.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        
        module_name = f"{folder.replace('/', '.')}.{py_file.stem}"
        
        try:
            module = importlib.import_module(module_name)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if hasattr(attr, "__tablename__") and not attr_name.startswith('_'):
                    # Deduplicar: solo agregar si no existe
                    if attr_name not in models_dict:
                        logger.debug(f"📦 Modelo encontrado: {attr_name} (tabla: {attr.__tablename__})")
                        models_dict[attr_name] = attr
                    else:
                        logger.debug(f"⚠️  Modelo duplicado omitido: {attr_name} en {module_name}")
        except Exception as e:
            logger.warning(f"⚠️  Error cargando {module_name}: {e}")
            continue
    
    models = list(models_dict.values())
    logger.info(f"✅ {len(models)} modelos únicos cargados")
    return models

def get_excluded_field_names_for_model(model):
    """Retorna lista de nombres de campos geometry/geography que deben excluirse"""
    excluded = []
    if not hasattr(model, '__table__'):
        return excluded
    
    for col in model.__table__.columns:
        col_type_str = str(col.type).lower()
        if 'geometry' in col_type_str or 'geography' in col_type_str:
            excluded.append(col.name)
    
    return excluded

def create_graphql_types(models):
    """Crea tipos GraphQL para todos los modelos soportando Relaciones"""
    type_registry = {}
    raw_classes = {}
    failed_models = []
    
    # PASO 1: Crear clases base (raw) para permitir referencias circulares
    for model in models:
        try:
            model_name = model.__name__
            # Creamos una clase vacía inicialmente
            raw_classes[model_name] = type(model_name, (), {
                "_model_class": model,
                "_property_methods": {}
            })
        except Exception as e:
            logger.warning(f"⚠️  Error inicializando clase para {model.__name__}: {e}")

    # PASO 2: Poblar anotaciones (Campos + Relaciones)
    for model in models:
        model_name = model.__name__
        if model_name not in raw_classes:
            continue
            
        cls = raw_classes[model_name]
        fields = {}
        
        try:
            # A. Columnas
            if hasattr(model, '__table__'):
                for column in model.__table__.columns:
                    field_name = column.name
                    graphql_type = get_graphql_type_for_column(column)
                    fields[field_name] = graphql_type
            
            # B. Relaciones
            insp = inspect(model)
            for rel in insp.relationships:
                target_model = rel.mapper.class_
                target_name = target_model.__name__
                
                # Solo mapear si el destino también está en nuestro registro
                if target_name in raw_classes:
                    target_cls = raw_classes[target_name]
                    
                    if rel.uselist:
                        fields[rel.key] = List[target_cls]
                    else:
                        fields[rel.key] = Optional[target_cls]
                else:
                    logger.debug(f"⚠️  Omitiendo relación {model_name}.{rel.key} (destino {target_name} desconocido)")

            # C. Propiedades (@property)
            for attr_name in dir(model):
                if attr_name.startswith('_'):
                    continue
                    
                attr = getattr(model, attr_name)
                if isinstance(attr, property) and attr.fget:
                    # Determinar tipo de retorno (simplificado)
                    return_type = Optional[str] # Default
                    sig = inspect.signature(attr.fget)
                    
                    if sig.return_annotation != inspect.Parameter.empty:
                        ann = sig.return_annotation
                        # Mapeo básico de tipos
                        if ann in (int, str, bool, float, datetime, date, Decimal):
                             # Ajustar a tipos GQL (opcionales por defecto para properties safe)
                             if ann == int: return_type = Optional[int]
                             elif ann == bool: return_type = Optional[bool]
                             elif ann == float: return_type = Optional[float]
                             elif ann == Decimal: return_type = Optional[float]
                             else: return_type = Optional[str]
                    
                    fields[attr_name] = return_type
                    cls._property_methods[attr_name] = attr.fget
            
            # Asignar anotaciones
            cls.__annotations__ = fields
            
        except Exception as e:
            logger.error(f"❌ Error procesando campos para {model_name}: {e}")
            failed_models.append((model_name, str(e)))

    # PASO 3: Convertir a Tipos Strawberry
    for model_name, cls in raw_classes.items():
        try:
            # Verificamos si falló en paso 2
            if not hasattr(cls, '__annotations__'):
                continue
                
            strawberry_type = strawberry.type(cls)
            type_registry[model_name] = strawberry_type
            logger.info(f"✅ Tipo {model_name} registrado (con relaciones)")
            
        except Exception as e:
            logger.error(f"❌ Error finalizando tipo {model_name}: {e}")
            failed_models.append((model_name, str(e)))
    
    return type_registry

def create_input_types(models, type_registry):
    """Crea input types para creación y actualización"""
    input_registry = {}
    
    for model_name, strawberry_type in type_registry.items():
        model = getattr(strawberry_type, '_model_class', None)
        if not model or not hasattr(model, '__table__'):
            continue
        
        # CREATE INPUT: solo columnas (no propiedades)
        create_fields = {}
        for column in model.__table__.columns:
            if column.name == 'id':
                continue
                
            field_type = get_graphql_type_for_column(column)
            # Para create, hacer campos requeridos (no Optional)
            if hasattr(field_type, '__origin__') and field_type.__origin__ == Optional:
                create_fields[column.name] = field_type.__args__[0]
            else:
                create_fields[column.name] = field_type
        
        if create_fields:
            CreateInput = strawberry.input(
                type(f"{model_name}CreateInput", (), {
                    "__annotations__": create_fields
                })
            )
            input_registry[f"{model_name}CreateInput"] = CreateInput
        
        # UPDATE INPUT: solo columnas (no propiedades), todas opcionales
        update_fields = {}
        for column in model.__table__.columns:
            if column.name == 'id':
                update_fields['id'] = strawberry.ID
            else:
                field_type = get_graphql_type_for_column(column)
                update_fields[column.name] = Optional[field_type]
        
        if update_fields:
            UpdateInput = strawberry.input(
                type(f"{model_name}UpdateInput", (), {
                    "__annotations__": update_fields
                })
            )
            input_registry[f"{model_name}UpdateInput"] = UpdateInput
    
    logger.info(f"✅ {len(input_registry)} input types creados")
    return input_registry

def convert_model_to_graphql(instance, strawberry_type):
    """Convierte instancia SQLAlchemy a instancia GraphQL"""
    if not instance:
        return None
    
    kwargs = {}
    
    # Campos de columna
    for field_name in strawberry_type.__annotations__.keys():
        if hasattr(instance, field_name):
            value = getattr(instance, field_name)
            
            # Convertir tipos especiales
            if isinstance(value, (datetime, date)):
                value = value.isoformat()
            elif isinstance(value, Decimal):
                value = float(value)
            
            kwargs[field_name] = value
    
    # Campos @property
    property_methods = getattr(strawberry_type, '_property_methods', {})
    for prop_name, fget in property_methods.items():
        if prop_name in strawberry_type.__annotations__:
            try:
                value = fget(instance)
                if isinstance(value, (datetime, date)):
                    value = value.isoformat()
                elif isinstance(value, Decimal):
                    value = float(value)
                kwargs[prop_name] = value
            except Exception as e:
                logger.debug(f"⚠️  Error en propiedad {prop_name}: {e}")
                kwargs[prop_name] = None
    
    return strawberry_type(**kwargs)

from app.graphql.strawchemy import create_filter_input_type, apply_strawchemy_filters
from app.graphql.spanish import pluralize

def lower_first(s: str) -> str:
    """Baja la primera letra de un string"""
    if not s:
        return s
    return s[0].lower() + s[1:]

def create_queries(models, type_registry):
    """Crea queries automáticas con soporte Strawchemy"""
    queries = {}
    
    for model_name, strawberry_type in type_registry.items():
        model = getattr(strawberry_type, '_model_class', None)
        if not model:
            continue
            
        # Generar Input Type para Filtros
        FilterInput = create_filter_input_type(model)
        
        # Query singular (get by id)
        async def get_one_resolver(
            info: strawberry.Info, 
            id: strawberry.ID
        ) -> Optional[strawberry_type]:
            try:
                db = info.context["request"].state.db
                stmt = select(model).where(model.id == id)
                result = await db.execute(stmt)
                instance = result.scalar_one_or_none()
                return convert_model_to_graphql(instance, strawberry_type)
            except Exception as e:
                logger.error(f"Error en get{model_name}: {e}")
                return None
        
        # Query plural con Filtros Strawchemy (list all)
        async def list_resolver(
            info: strawberry.Info,
            filter: Optional[FilterInput] = None,
            limit: int = 50,
            offset: int = 0
        ) -> List[strawberry_type]:
            try:
                db = info.context["request"].state.db
                stmt = select(model)
                
                # Aplicar filtros Strawchemy
                if filter:
                    stmt = apply_strawchemy_filters(stmt, filter, model)
                
                stmt = stmt.offset(offset).limit(limit)
                
                result = await db.execute(stmt)
                instances = result.scalars().all()
                return [convert_model_to_graphql(inst, strawberry_type) for inst in instances]
            except Exception as e:
                logger.error(f"Error en list{model_name}s: {e}")
                return []
        
        # Añadir anotaciones de retorno
        get_one_resolver.__annotations__['return'] = Optional[strawberry_type]
        list_resolver.__annotations__['return'] = List[strawberry_type]
        
        # Nombres de queries
        plural_name = pluralize(model_name)
        
        # Registrar queries
        # 1. Singular standard
        queries[f"get{model_name}"] = strawberry.field(get_one_resolver)
        
        # 2. Plural corto (convención frontend: 'tecnicos', 'agenciasInmobiliarias')
        queries[lower_first(plural_name)] = strawberry.field(list_resolver)
        
        # 3. Alias list{Name}s por compatibilidad (listAgenciaInmobiliarias)
        queries[f"list{plural_name}"] = strawberry.field(list_resolver)  # Usar plural_name aquí también es mejor práctica
        # Mantenemos list{Model}s para absoluta backward compatibility si fuera necesario, 
        # pero list{Plural} es más limpio. Frontend usa plural corto ahora.
        queries[f"list{model_name}s"] = strawberry.field(list_resolver)

    logger.info(f"✅ {len(queries)} queries creadas")
    return queries

def create_mutations(models, type_registry, input_registry):
    """Crea mutations automáticas"""
    mutations = {}
    
    for model_name, strawberry_type in type_registry.items():
        model = getattr(strawberry_type, '_model_class', None)
        if not model:
            continue
            
        FilterInput = create_filter_input_type(model)
        plural_name = pluralize(model_name)
        
        # CREATE mutation
        if f"{model_name}CreateInput" in input_registry:
            CreateInput = input_registry[f"{model_name}CreateInput"]
            
            async def create_resolver(
                info: strawberry.Info,
                data: CreateInput
            ) -> Optional[strawberry_type]:
                try:
                    db = info.context["request"].state.db
                    
                    # Extraer datos (solo columnas)
                    data_dict = {}
                    if hasattr(model, '__table__'):
                        for column in model.__table__.columns:
                            col_name = column.name
                            if col_name != 'id' and hasattr(data, col_name):
                                value = getattr(data, col_name)
                                if value is not None:
                                    data_dict[col_name] = value
                    
                    # Crear instancia
                    instance = model(**data_dict)
                    db.add(instance)
                    await db.commit()
                    await db.refresh(instance)
                    
                    return convert_model_to_graphql(instance, strawberry_type)
                except Exception as e:
                    logger.error(f"Error en create{model_name}: {e}")
                    await db.rollback()
                    return None
            
            create_resolver.__annotations__['return'] = Optional[strawberry_type]
            mutations[f"create{model_name}"] = strawberry.mutation(create_resolver)
            
            # Alias frontend update convention? Frontend uses create{Model} usually.
        
        # DELETE mutation (Singular standard)
        async def delete_resolver(
            info: strawberry.Info,
            id: strawberry.ID
        ) -> bool:
            try:
                db = info.context["request"].state.db
                
                stmt = select(model).where(model.id == id)
                result = await db.execute(stmt)
                instance = result.scalar_one_or_none()
                
                if not instance:
                    return False
                
                await db.delete(instance)
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"Error en delete{model_name}: {e}")
                await db.rollback()
                return False
        
        delete_resolver.__annotations__['return'] = bool
        mutations[f"delete{model_name}"] = strawberry.mutation(delete_resolver)
        
        # DELETE MANY mutation (Frontend convention: deleteTecnicos(filter: ...))
        async def delete_many_resolver(
            info: strawberry.Info,
            filter: FilterInput
        ) -> List[strawberry_type]:
            try:
                db = info.context["request"].state.db
                stmt = select(model)
                stmt = apply_strawchemy_filters(stmt, filter, model)
                
                result = await db.execute(stmt)
                instances = result.scalars().all()
                
                deleted_items = []
                for instance in instances:
                    item_data = convert_model_to_graphql(instance, strawberry_type)
                    deleted_items.append(item_data)
                    await db.delete(instance)
                
                await db.commit()
                return deleted_items
            except Exception as e:
                logger.error(f"Error en delete{plural_name}: {e}")
                await db.rollback()
                return []

        delete_many_resolver.__annotations__['return'] = List[strawberry_type]
        mutations[f"delete{plural_name}"] = strawberry.mutation(delete_many_resolver)
    
    logger.info(f"✅ {len(mutations)} mutations creadas")
    return mutations

def create_schema(models_folder: str = "app/db/models") -> strawberry.Schema:
    """Función principal que crea el schema GraphQL completo"""
    logger.info("🚀 Iniciando creación de schema GraphQL")
    
    try:
        # 1. Cargar modelos
        models = load_all_models(models_folder)
        if not models:
            logger.error("❌ No se encontraron modelos")
            raise ValueError("No se encontraron modelos")
        
        # 2. Crear tipos GraphQL
        type_registry = create_graphql_types(models)
        if not type_registry:
            logger.error("❌ No se pudieron crear tipos GraphQL")
            raise ValueError("No se pudieron crear tipos GraphQL")
        
        # 3. Crear input types
        input_registry = create_input_types(models, type_registry)
        
        # 4. Crear queries
        queries = create_queries(models, type_registry)
        
        # 5. Crear mutations
        mutations = create_mutations(models, type_registry, input_registry)
        
        # 6. Verificar que hay queries y mutations
        if not queries or not mutations:
            logger.error("❌ No se generaron queries o mutations")
            raise ValueError("No se generaron queries o mutations")
        
        # 7. Crear tipos Query y Mutation finales
        Query = strawberry.type(type("Query", (), queries))
        Mutation = strawberry.type(type("Mutation", (), mutations))
        
        # 8. Crear schema
        schema = strawberry.Schema(query=Query, mutation=Mutation)
        
        logger.info("🎉 Schema creado exitosamente")
        logger.info(f"   • Modelos procesados: {len(models)}")
        logger.info(f"   • Tipos GraphQL: {len(type_registry)}")
        logger.info(f"   • Queries: {len(queries)}")
        logger.info(f"   • Mutations: {len(mutations)}")
        
        return schema
        
    except Exception as e:
        logger.error(f"❌ Error creando schema: {e}", exc_info=True)
        raise