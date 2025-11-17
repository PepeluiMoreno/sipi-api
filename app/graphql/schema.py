"""GraphQL Schema Auto-Generator"""
from pathlib import Path
import importlib
from typing import List, Type, Optional
import strawberry
from app.graphql.types import FilterInput, SortInput, PaginationInput, PaginatedResult
from app.graphql.decorators import async_safe_resolver
from app.graphql.mapper.enhanced_mapper import EnhancedSQLAlchemyMapper
from app.graphql.mapper.crud import CRUDResolver

mapper = EnhancedSQLAlchemyMapper()

def load_models_from_folder(folder: str) -> List[Type]:
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
    queries = {}
    mutations = {}
    
    for model in models:
        model_name = model.__name__
        name_prefix = model_name.lower()
        
        # ✅ CORRECCIÓN: Capturar variables en el closure con valores por defecto
        crud = CRUDResolver(model, mapper)
        strawberry_type = mapper.type(model)
        create_input = mapper.input_type(model, "Create")
        update_input = mapper.input_type(model, "Update", optional=True)
        
        # Query: Get one
        @async_safe_resolver
        async def get_one(info, id: strawberry.ID, _crud=crud):
            db = info.context["db"]
            return await _crud.get(db, id)
        
        # Query: Get many
        @async_safe_resolver
        async def get_many(
            info, 
            filters: Optional[List[FilterInput]] = None,
            sort: Optional[List[SortInput]] = None,
            pagination: Optional[PaginationInput] = None,
            _crud=crud
        ):
            db = info.context["db"]
            return await _crud.list(db, filters, sort, pagination)
        
        queries[f"{name_prefix}"] = strawberry.field(resolver=get_one)
        queries[f"{name_prefix}s"] = strawberry.field(resolver=get_many)
        
        # Mutation: Create
        @async_safe_resolver
        async def create_one(info, data: create_input, _crud=crud):
            db = info.context["db"]
            return await _crud.create(db, data.__dict__)
        
        # Mutation: Update
        @async_safe_resolver
        async def update_one(info, id: strawberry.ID, data: update_input, _crud=crud):
            db = info.context["db"]
            return await _crud.update(db, id, data.__dict__)
        
        # Mutation: Delete
        @async_safe_resolver
        async def delete_one(info, id: strawberry.ID, _crud=crud):
            db = info.context["db"]
            return await _crud.delete(db, id)
        
        mutations[f"create{model_name}"] = strawberry.mutation(resolver=create_one)
        mutations[f"update{model_name}"] = strawberry.mutation(resolver=update_one)
        mutations[f"delete{model_name}"] = strawberry.mutation(resolver=delete_one)
        
        # Mutation: Restore (solo si el modelo tiene soft delete)
        if hasattr(model, "deleted_at"):
            @async_safe_resolver
            async def restore_one(info, id: strawberry.ID, _crud=crud):
                db = info.context["db"]
                return await _crud.restore(db, id)
            
            mutations[f"restore{model_name}"] = strawberry.mutation(resolver=restore_one)
    
    Query = type("Query", (), queries)
    Mutation = type("Mutation", (), mutations)
    
    return Query, Mutation

def create_schema(models_folder: str = "app/db/models") -> strawberry.Schema:
    models = load_models_from_folder(models_folder)
    Query, Mutation = generate_resolvers(models)
    
    return strawberry.Schema(
        query=Query,
        mutation=Mutation,
        extensions=[strawberry.extensions.QueryDepthLimiter(max_depth=10)],
    )

schema = create_schema()