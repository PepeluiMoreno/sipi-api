"""GraphQL Schema Auto-Generator"""
from pathlib import Path
import importlib
from typing import List, Type, Optional, Any, TYPE_CHECKING
import strawberry
from strawberry.types import Info
from app.graphql.types import FilterInput, SortInput, PaginationInput, PaginatedResult
from app.graphql.decorators import async_safe_resolver
from app.graphql.mapper.enhanced_mapper import EnhancedSQLAlchemyMapper
from app.graphql.mapper.crud import CRUDResolver
from app.core.config import GRAPHQL_MAX_DEPTH

if TYPE_CHECKING:
    from app.graphql.mapper.crud import CRUDResolver

mapper = EnhancedSQLAlchemyMapper()

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

def generate_resolvers(models: List[Type]) -> tuple:
    """Genera resolvers GraphQL dinámicamente para todos los modelos"""
    queries = {}
    mutations = {}
    
    for model in models:
        model_name = model.__name__
        name_prefix = model_name.lower()
        
        crud: CRUDResolver = CRUDResolver(model, mapper)
        strawberry_type = mapper.type(model)
        create_input = mapper.input_type(model, "Create")
        update_input = mapper.input_type(model, "Update", optional=True)
        
        # ==================== QUERIES ====================
        
        @async_safe_resolver
        async def get_one(
            info: Info, 
            id: strawberry.ID, 
            _crud: "CRUDResolver" = crud
        ) -> Optional[Any]:
            """Obtiene un registro por ID"""
            db = info.context["db"]
            return await _crud.get(db, id)
        
        @async_safe_resolver
        async def get_many(
            info: Info,
            filters: Optional[List[FilterInput]] = None,
            sort: Optional[List[SortInput]] = None,
            pagination: Optional[PaginationInput] = None,
            _crud: "CRUDResolver" = crud
        ) -> PaginatedResult:
            """Obtiene lista de registros con filtros, orden y paginación"""
            db = info.context["db"]
            return await _crud.list(db, filters, sort, pagination)
        
        queries[f"{name_prefix}"] = strawberry.field(resolver=get_one)
        queries[f"{name_prefix}s"] = strawberry.field(resolver=get_many)
        
        # ==================== MUTATIONS ====================
        
        @async_safe_resolver
        async def create_one(
            info: Info, 
            data: create_input, 
            _crud: "CRUDResolver" = crud
        ) -> Any:
            """Crea un nuevo registro"""
            db = info.context["db"]
            return await _crud.create(db, data.__dict__)
        
        @async_safe_resolver
        async def update_one(
            info: Info, 
            id: strawberry.ID, 
            data: update_input, 
            _crud: "CRUDResolver" = crud
        ) -> Optional[Any]:
            """Actualiza un registro existente"""
            db = info.context["db"]
            return await _crud.update(db, id, data.__dict__)
        
        @async_safe_resolver
        async def delete_one(
            info: Info, 
            id: strawberry.ID, 
            _crud: "CRUDResolver" = crud
        ) -> bool:
            """Elimina (soft o hard) un registro"""
            db = info.context["db"]
            return await _crud.delete(db, id)
        
        mutations[f"create{model_name}"] = strawberry.mutation(resolver=create_one)
        mutations[f"update{model_name}"] = strawberry.mutation(resolver=update_one)
        mutations[f"delete{model_name}"] = strawberry.mutation(resolver=delete_one)
        
        if hasattr(model, "deleted_at"):
            @async_safe_resolver
            async def restore_one(
                info: Info, 
                id: strawberry.ID, 
                _crud: "CRUDResolver" = crud
            ) -> Optional[Any]:
                """Restaura un registro soft-deleted"""
                db = info.context["db"]
                return await _crud.restore(db, id)
            
            mutations[f"restore{model_name}"] = strawberry.mutation(resolver=restore_one)
    
    # ✅ Crear tipos Strawberry dinámicamente
    Query = strawberry.type(type("Query", (), queries))
    Mutation = strawberry.type(type("Mutation", (), mutations))
    
    return Query, Mutation

def create_schema(models_folder: str = "app/db/models") -> strawberry.Schema:
    """Crea y retorna el schema GraphQL completo"""
    print(f"📂 Cargando modelos desde: {models_folder}")
    models = load_models_from_folder(models_folder)
    Query, Mutation = generate_resolvers(models)
    
    print(f"🚀 GraphQL Schema creado con {len(models)} modelos")
    return strawberry.Schema(
        query=Query,
        mutation=Mutation,
        extensions=[
            strawberry.extensions.QueryDepthLimiter(
                max_depth=GRAPHQL_MAX_DEPTH
            )
        ],
    )

# ✅ Schema global (para importar en app.py)
schema = create_schema()