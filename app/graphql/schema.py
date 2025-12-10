# app/graphql/schema.py
"""GraphQL Schema Auto-Generator"""
from pathlib import Path
import importlib
from typing import List, Type, Optional, Dict
import strawberry
from strawberry.types import Info
from app.graphql.types import FilterInput, SortInput, PaginationInput, PageInfo
from app.graphql.decorators import async_safe_resolver

from app.graphql.mapper.crud import CRUDResolver
from app.core.config import GRAPHQL_MAX_DEPTH

from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper

mapper = StrawberrySQLAlchemyMapper()

# from app.graphql.mapper import SQLAlchemyMapper # Custom mapper removed
 
# Importar configuración de pluralización
try:
    from app.graphql.spanish import PLURALES_INVARIABLES, PLURALES_EXCEPCIONES
    print(f"📋 Config español: {len(PLURALES_INVARIABLES)} invariables, {len(PLURALES_EXCEPCIONES)} excepciones")
except ImportError:
    print("⚠️  Archivo de config español no encontrado, usando valores por defecto")
    PLURALES_INVARIABLES = {'crisis', 'tesis', 'sintesis', 'analisis', 'diocesis'}
    PLURALES_EXCEPCIONES = {}

# mapper = EnhancedSQLAlchemyMapper() # Custom mapper removed
mapper = StrawberrySQLAlchemyMapper()

def pluralize_spanish(word: str) -> str:
    """
    Pluraliza palabras en español usando reglas lingüísticas.
    Lee palabras invariables y excepciones desde config.
    """
    word_lower = word.lower()
    
    # Consultar excepciones primero
    if word_lower in PLURALES_EXCEPCIONES:
        return PLURALES_EXCEPCIONES[word_lower]
    
    # Palabras invariables (desde config)
    if word_lower in PLURALES_INVARIABLES or any(word_lower.endswith(inv) for inv in PLURALES_INVARIABLES):
        return word_lower
    
    # Regla 1: Termina en -ción → -ciones
    if word_lower.endswith('cion'):
        return word_lower + 'es'
    
    # Regla 2: Termina en -sión → -siones  
    if word_lower.endswith('sion'):
        return word_lower + 'es'
    
    # Regla 3: Termina en -z → -ces
    if word_lower.endswith('z'):
        return word_lower[:-1] + 'ces'
    
    # Regla 4: Termina en vocal átona (a, e, i, o, u) → +s
    if len(word_lower) > 1 and word_lower[-1] in 'aeiou':
        return word_lower + 's'
    
    # Regla 5: Termina en -í o -ú (vocal tónica) → +es
    if word_lower.endswith(('í', 'ú')):
        return word_lower + 'es'
    
    # Regla 6: Termina en consonante (excepto -s, -x) → +es
    if word_lower[-1] not in 'aeiousx':
        return word_lower + 'es'
    
    # Regla 7: Ya termina en -s (invariable por defecto)
    if word_lower.endswith('s'):
        return word_lower
    
    # Por defecto: +s
    return word_lower + 's'

def load_models_from_folder(folder: str) -> List[Type]:
    """Carga todos los modelos SQLAlchemy desde una carpeta"""
    models = []
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"❌ Carpeta no encontrada: {folder}")
    
    for py_file in folder_path.glob("*.py"):
        if py_file.name.startswith("__"):
            continue
        module_name = f"{folder.replace('/', '.')}.{py_file.stem}"
        module = importlib.import_module(module_name)
        
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if hasattr(attr, "__tablename__"):
                models.append(attr)
    
    print(f"✅ {len(models)} modelos cargados")
    return models

def create_paginated_type(item_type: Type, model_name: str) -> Type:
    """Crea un tipo PaginatedResult específico para un modelo"""
    
    @strawberry.type(name=f"{model_name}Paginated")
    class PaginatedType:
        items: List[item_type]
        page_info: PageInfo
    
    return PaginatedType

def generate_resolvers(models: List[Type]) -> tuple:
    """Genera resolvers GraphQL dinámicamente para todos los modelos"""
    queries = {}
    mutations = {}
    
    # Pre-registrar todos los tipos Strawberry
    type_registry: Dict[str, Type] = {}
    paginated_registry: Dict[str, Type] = {}
    
    print(f"\n{'='*70}")
    print(f"🔍 Mapeando {len(models)} modelos a tipos Strawberry...")
    print(f"📋 Modelos encontrados: {[m.__name__ for m in models]}")
    print(f"{'='*70}\n")
    
    for model in models:
        try:
            model_name = model.__name__
            print(f"📝 Procesando {model_name}...")
            
            # Crear tipo base
            print(f"  → Creando tipo Strawberry...")
            
            # ✅ Solución: usar mapper.type(model) como clase base para la herencia dinámica.
            # Esto fuerza la inyección de campos (incluyendo relaciones) antes de que
            # strawberry.type decore la clase, resolviendo el problema de las relaciones.
            BaseType = mapper.type(model)
            
            @strawberry.type(name=model_name)
            class DynamicType(BaseType):
                pass
            
            strawberry_type = DynamicType
            print(f"  → Tipo creado: {strawberry_type}")
            
            type_registry[model_name] = strawberry_type
            
            # Crear tipo paginado
            print(f"  → Creando tipo paginado...")
            paginated_type = create_paginated_type(strawberry_type, model_name)
            paginated_registry[model_name] = paginated_type
            
            print(f"  ✅ {model_name} mapeado correctamente\n")
        
        except Exception as e:
            print(f"  ❌ ERROR en {model_name}: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            print()
            continue
    
    print(f"\n{'='*70}")
    print(f"✅ {len(type_registry)}/{len(models)} tipos mapeados correctamente")
    print(f"📋 Tipos exitosos: {list(type_registry.keys())}")
    print(f"{'='*70}\n")
    
    if not type_registry:
        print("\n❌ NINGÚN MODELO SE PUDO MAPEAR")
        print("Revisa los errores arriba para ver qué falló")
        raise ValueError("❌ No se pudo mapear ningún modelo")
    
    # Generar resolvers para cada modelo
    print(f"🔨 Generando resolvers...")
    
    for model in models:
        if model.__name__ not in type_registry:
            print(f"  ⏭️  Saltando {model.__name__} (no se pudo mapear)")
            continue
            
        model_name = model.__name__
        name_prefix = model_name.lower()
        name_plural = pluralize_spanish(model_name)
        
        print(f"  🔧 {model_name} → {name_prefix} / {name_plural}")
        
        crud = CRUDResolver(model, mapper)
        strawberry_type = type_registry[model_name]
        paginated_type = paginated_registry[model_name]
        
        try:
            create_input = mapper.input_type(model, name=f"{model_name}CreateInput")
            update_input = mapper.input_type(model, name=f"{model_name}UpdateInput", partial=True)
        except Exception as e:
            print(f"    ⚠️  No se pudo crear inputs para {model_name}: {e}")
            continue
        
        # ==================== QUERIES ====================
        # ✅ Crear funciones con anotaciones correctas usando setattr
        
        # Query: obtener uno por ID
        def make_get_one_func(crud_inst, ret_type):
            async def resolver(info: Info, id: strawberry.ID):
                db = info.context["db"]
                return await crud_inst.get(db, id)
            # ✅ Añadir anotación de retorno manualmente
            resolver.__annotations__['return'] = Optional[ret_type]
            return async_safe_resolver(resolver)
        
        # Query: obtener lista paginada
        def make_get_many_func(crud_inst, pag_type):
            async def resolver(
                info: Info,
                filters: Optional[List[FilterInput]] = None,
                sort: Optional[List[SortInput]] = None,
                pagination: Optional[PaginationInput] = None,
            ):
                db = info.context["db"]
                result = await crud_inst.list(db, filters, sort, pagination)
                return pag_type(items=result.items, page_info=result.page_info)
            # ✅ Añadir anotación de retorno manualmente
            resolver.__annotations__['return'] = pag_type
            return async_safe_resolver(resolver)
        
        queries[f"{name_prefix}"] = strawberry.field(
            resolver=make_get_one_func(crud, strawberry_type)
        )
        queries[f"{name_plural}"] = strawberry.field(
            resolver=make_get_many_func(crud, paginated_type)
        )
        
        # ==================== MUTATIONS ====================
        
        # Mutation: crear
        def make_create_func(crud_inst, inp_type, ret_type):
            async def resolver(info: Info, data: inp_type):
                db = info.context["db"]
                return await crud_inst.create(db, data.__dict__)
            resolver.__annotations__['return'] = ret_type
            return async_safe_resolver(resolver)
        
        # Mutation: actualizar
        def make_update_func(crud_inst, inp_type, ret_type):
            async def resolver(info: Info, id: strawberry.ID, data: inp_type):
                db = info.context["db"]
                return await crud_inst.update(db, id, data.__dict__)
            resolver.__annotations__['return'] = Optional[ret_type]
            return async_safe_resolver(resolver)
        
        # Mutation: eliminar
        def make_delete_func(crud_inst):
            async def resolver(info: Info, id: strawberry.ID) -> bool:
                db = info.context["db"]
                return await crud_inst.delete(db, id)
            return async_safe_resolver(resolver)
        
        mutations[f"create{model_name}"] = strawberry.mutation(
            resolver=make_create_func(crud, create_input, strawberry_type)
        )
        mutations[f"update{model_name}"] = strawberry.mutation(
            resolver=make_update_func(crud, update_input, strawberry_type)
        )
        mutations[f"delete{model_name}"] = strawberry.mutation(
            resolver=make_delete_func(crud)
        )
        
        # Mutation: restore (solo si tiene soft delete)
        if hasattr(model, "deleted_at"):
            def make_restore_func(crud_inst, ret_type):
                async def resolver(info: Info, id: strawberry.ID):
                    db = info.context["db"]
                    return await crud_inst.restore(db, id)
                resolver.__annotations__['return'] = Optional[ret_type]
                return async_safe_resolver(resolver)
            
            mutations[f"restore{model_name}"] = strawberry.mutation(
                resolver=make_restore_func(crud, strawberry_type)
            )
    
    print(f"  ✅ Resolvers generados\n")
    
    # Crear tipos Query y Mutation
    print(f"🏗️  Creando tipos GraphQL Query y Mutation...")
    Query = strawberry.type(type("Query", (), queries))
    Mutation = strawberry.type(type("Mutation", (), mutations))
    print(f"  ✅ Tipos creados\n")
    
    return Query, Mutation

def create_schema(models_folder: str = "app/db/models") -> strawberry.Schema:
    """Crea y retorna el schema GraphQL completo"""
    print(f"\n{'='*70}")
    print(f"📂 INICIANDO GENERACIÓN DE SCHEMA GRAPHQL")
    print(f"{'='*70}\n")
    
    print(f"📂 Cargando modelos desde: {models_folder}")
    models = load_models_from_folder(models_folder)
    
    print(f"\n🔨 Generando schema GraphQL...")
    Query, Mutation = generate_resolvers(models)
    
    print(f"{'='*70}")
    print(f"🚀 GraphQL Schema creado exitosamente")
    print(f"   • Modelos: {len(models)}")
    print(f"   • Tipos GraphQL generados")
    print(f"{'='*70}\n")
    
    return strawberry.Schema(
        query=Query,
        mutation=Mutation,
        extensions=[
            strawberry.extensions.QueryDepthLimiter(
                max_depth=GRAPHQL_MAX_DEPTH
            )
        ],
    )

# Schema global
schema = create_schema()