# app/graphql/schema.py
from pathlib import Path
from typing import List, Type, Optional, Dict
import strawberry
from strawberry.types import Info
from strawberry_sqlalchemy_mapper import StrawberrySQLAlchemyMapper

from app.graphql.mapper import mapper
from app.graphql.types import FilterInput, SortInput, PaginationInput, PageInfo as PageInfoBase
from app.graphql.crud import CRUDResolver
from app.graphql.spanish import pluralize

import logging
logger = logging.getLogger(__name__)

PageInfo = strawberry.type(PageInfoBase)

_original_convert = getattr(StrawberrySQLAlchemyMapper, "_convert_column_to_strawberry_type", None)

def _safe_convert_column_to_strawberry_type(self, column):
    try:
        col_type = getattr(column, "type", None)
        if col_type is not None:
            tname = getattr(col_type.__class__, "__name__", "").lower()
            tmod = getattr(col_type.__class__, "__module__", "").lower()
            if any(k in tname for k in ("geometry", "geography", "wkb", "ewkb", "point")) or "geoalchemy2" in tmod:
                return Optional[str]
    except Exception:
        pass
    return _original_convert(self, column) if _original_convert else None

if not getattr(StrawberrySQLAlchemyMapper, "_patched_safe_convert", False):
    StrawberrySQLAlchemyMapper._convert_column_to_strawberry_type = _safe_convert_column_to_strawberry_type
    StrawberrySQLAlchemyMapper._patched_safe_convert = True


_paginated_cache: Dict[str, Type] = {}

def create_paginated_type(item_type: Type, model_name: str) -> Type:
    if model_name in _paginated_cache:
        return _paginated_cache[model_name]
    
    def __init__(self, items, page_info):
        self.items = items
        self.page_info = page_info
    
    PaginatedClass = type(
        f"{model_name}Paginated",
        (),
        {
            '__init__': __init__,
            '__annotations__': {
                'items': List[item_type],
                'page_info': PageInfo
            }
        }
    )
    
    StrawberryPaginated = strawberry.type(PaginatedClass)
    _paginated_cache[model_name] = StrawberryPaginated
    return StrawberryPaginated


def create_schema() -> strawberry.Schema:
    logger.info("[START]")
    
    # Importar modelos desde __init__.py (orden correcto de dependencias)
    from app.db.models import (
        Adquiriente, Administracion, AdministracionTitular, AgenciaInmobiliaria,
        ColegioProfesional, Diocesis, DiocesisTitular, Notaria,
        Tecnico, RegistroPropiedad, RegistroPropiedadTitular, Transmitente,
        TipoEstadoConservacion, TipoEstadoTratamiento, TipoRolTecnico,
        TipoCertificacionPropiedad, TipoDocumento, TipoInmueble, TipoMimeDocumento,
        TipoPersona, TipoTransmision, TipoVia, TipoLicencia, FuenteDocumental,
        ComunidadAutonoma, Provincia, Municipio,
        Documento, InmuebleDocumento, ActuacionDocumento, TransmisionDocumento,
        Actuacion, ActuacionTecnico,
        Transmision, TransmisionAnunciante,
        Inmueble, Inmatriculacion, InmuebleDenominacion, InmuebleOSMExt, InmuebleWDExt, InmuebleCita,
        FuenteHistoriografica,
        FiguraProteccion,
        ActuacionSubvencion, SubvencionAdministracion,
        Usuario, Rol
    )
    
    models = [
        ComunidadAutonoma, Provincia, Municipio,
        TipoEstadoConservacion, TipoEstadoTratamiento, TipoRolTecnico,
        TipoCertificacionPropiedad, TipoDocumento, TipoInmueble, TipoMimeDocumento,
        TipoPersona, TipoTransmision, TipoVia, TipoLicencia, FuenteDocumental,
        FuenteHistoriografica, FiguraProteccion,
        Adquiriente, Administracion, AdministracionTitular, AgenciaInmobiliaria,
        ColegioProfesional, Diocesis, DiocesisTitular, Notaria,
        Tecnico, RegistroPropiedad, RegistroPropiedadTitular, Transmitente,
        Documento, InmuebleDocumento, ActuacionDocumento, TransmisionDocumento,
        Actuacion, ActuacionTecnico,
        Transmision, TransmisionAnunciante,
        ActuacionSubvencion, SubvencionAdministracion,
        Usuario, Rol,
        Inmueble, Inmatriculacion, InmuebleDenominacion, InmuebleOSMExt, InmuebleWDExt, InmuebleCita
    ]
    
    logger.info(f"OK {len(models)} models imported")
    
    # CRÍTICO: Forzar que SQLAlchemy configure TODOS los mappers antes de strawberry
    from sqlalchemy.orm import configure_mappers
    try:
        configure_mappers()
        logger.info("OK SQLAlchemy mappers configured")
    except Exception as e:
        logger.error(f"ERR configuring SQLAlchemy mappers: {e}")
        raise
    
    # Mapear modelos
    type_registry = {}
    for model in models:
        try:
            model_name = model.__name__
            
            if hasattr(mapper, '_type_map') and model in mapper._type_map:
                strawberry_type = mapper._type_map[model]
                type_registry[model_name] = strawberry_type
                logger.info(f"[CACHED] {model_name}")
                continue
            
            decorator = mapper.type(model)
            BaseClass = type(f'Type_{id(model)}', (), {})
            strawberry_type = decorator(BaseClass)
            type_registry[model_name] = strawberry_type
            logger.info(f"[OK] {model_name}")
        except Exception as e:
            logger.error(f"[ERR] {model_name}: {e}")
    
    logger.info(f"OK {len(type_registry)} types")
    
    if not type_registry:
        raise ValueError("ERROR type_registry empty")
    
    # Tipos paginados
    logger.info("[PAGINATED]")
    paginated_registry = {}
    for model_name, strawberry_type in type_registry.items():
        try:
            paginated_type = create_paginated_type(strawberry_type, model_name)
            paginated_registry[model_name] = paginated_type
        except Exception as e:
            logger.error(f"[ERR] {model_name}Paginated: {e}")
    
    logger.info(f"OK {len(paginated_registry)} paginated")
    
    # Resolvers
    logger.info("[RESOLVERS]")
    queries = {}
    mutations = {}
    
    for model in models:
        model_name = model.__name__
        if model_name not in type_registry or model_name not in paginated_registry:
            continue
        
        name_single = model_name.lower()
        name_plural = pluralize(name_single)
        
        crud = CRUDResolver(model, mapper)
        model_type = type_registry[model_name]
        paginated_type = paginated_registry[model_name]
        
        def make_get(c, t):
            async def resolver(info: Info, id: strawberry.ID):
                return await c.get(info.context["request"].state.db, id)
            resolver.__annotations__['return'] = Optional[t]
            return resolver
        
        queries[name_single] = strawberry.field(make_get(crud, model_type))
        
        def make_list(c, pt):
            async def resolver(
                info: Info,
                filters: Optional[List[FilterInput]] = None,
                sort: Optional[List[SortInput]] = None,
                pagination: Optional[PaginationInput] = None,
            ):
                result = await c.list(info.context["request"].state.db, filters, sort, pagination)
                return pt(items=result.items, page_info=result.page_info)
            resolver.__annotations__['return'] = pt
            return resolver
        
        queries[name_plural] = strawberry.field(make_list(crud, paginated_type))
        
        def make_delete(c):
            async def resolver(info: Info, id: strawberry.ID) -> bool:
                return await c.delete(info.context["request"].state.db, id)
            return resolver
        
        mutations[f"delete{model_name}"] = strawberry.mutation(make_delete(crud))
        
        try:
            create_input = mapper.input_type(model, name=f"{model_name}CreateInput")
            def make_create(c, inp, t):
                async def resolver(info: Info, data: inp):
                    return await c.create(info.context["request"].state.db, data.__dict__)
                resolver.__annotations__['return'] = t
                return resolver
            mutations[f"create{model_name}"] = strawberry.mutation(make_create(crud, create_input, model_type))
        except:
            pass
        
        try:
            update_input = mapper.input_type(model, name=f"{model_name}UpdateInput", partial=True)
            def make_update(c, inp, t):
                async def resolver(info: Info, id: strawberry.ID, data: inp):
                    return await c.update(info.context["request"].state.db, id, data.__dict__)
                resolver.__annotations__['return'] = Optional[t]
                return resolver
            mutations[f"update{model_name}"] = strawberry.mutation(make_update(crud, update_input, model_type))
        except:
            pass
    
    logger.info(f"OK {len(queries)} queries, {len(mutations)} mutations")
    
    if not queries:
        raise ValueError("ERROR No queries")
    
    mapper.finalize()
    
    Query = strawberry.type(type("Query", (), queries))
    Mutation = strawberry.type(type("Mutation", (), mutations))
    
    schema = strawberry.Schema(query=Query, mutation=Mutation)
    
    logger.info("[DONE]")
    return schema