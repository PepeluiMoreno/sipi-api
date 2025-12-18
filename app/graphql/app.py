# app/graphql/app.py - VERSIÓN OPTIMIZADA
from typing import Any, Dict
import threading
import traceback

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse, HTMLResponse, Response
from starlette.routing import Route, Mount
from starlette.requests import Request

from sipi.db.sessions.async_session import async_session_maker

# Variables globales para la app GraphQL (creación lazy)
_schema = None
_graphql_asgi = None
_schema_lock = threading.Lock()
_schema_created = False


def _create_graphql_assets():
    """
    Crea schema y GraphQL ASGI app de forma atómica (con lock).
    """
    global _schema, _graphql_asgi, _schema_created

    if _schema_created and _graphql_asgi is not None:
        return _schema, _graphql_asgi

    with _schema_lock:
        if _schema_created and _graphql_asgi is not None:
            return _schema, _graphql_asgi

        try:
            from app.graphql.schema import create_schema
            from strawberry.asgi import GraphQL

            print("[FIX] Creating schema GraphQL (lazy)...")
            _schema = create_schema()
            _graphql_asgi = GraphQL(_schema, graphiql=True)
            _schema_created = True
            print("OK Schema GraphQL created")
            return _schema, _graphql_asgi
        except Exception as e:
            print("ERROR Error creando schema GraphQL:", e)
            print(traceback.format_exc())
            raise


# Rutas
async def docs_page(request: Request):
    return HTMLResponse("""
    <html>
    <head><title>SIPI GraphQL API</title></head>
    <body style="font-family: sans-serif; max-width: 800px; margin: 50px auto;">
        <h1>[API] SIPI GraphQL API</h1>
        <ul>
            <li><a href="/graphql">GraphiQL GraphiQL</a></li>
            <li><a href="/schema.graphql">Schema Schema SDL</a></li>
            <li><a href="/stats">Stats Stats</a></li>
        </ul>
    </body>
    </html>
    """)


async def health(request: Request):
    return JSONResponse({"status": "ok", "service": "graphql"})


async def export_schema(request: Request):
    try:
        schema, _ = _create_graphql_assets()
    except Exception as e:
        return PlainTextResponse(f"Error: {e}\n{traceback.format_exc()}", status_code=500)
    
    try:
        if hasattr(schema, "as_str"):
            return PlainTextResponse(schema.as_str())
    except Exception:
        pass
    return PlainTextResponse(str(schema))


async def schema_stats(request: Request):
    """Endpoint de estadísticas del schema GraphQL"""
    try:
        schema, _ = _create_graphql_assets()
    except Exception as e:
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc()
        }, status_code=500)

    # Obtener tipos del schema (Strawberry usa schema_converter)
    try:
        if hasattr(schema, 'schema_converter'):
            type_map = schema.schema_converter.type_map
        elif hasattr(schema, '_schema'):
            # Fallback para versiones diferentes
            type_map = schema._schema.type_map
        else:
            type_map = {}
        
        # Contar tipos (excluir internos que empiezan con __)
        num_types = len([t for t in type_map.keys() if not str(t).startswith('__')])
    except Exception:
        num_types = 0
    
    # Obtener queries y mutations
    queries = {}
    mutations = {}
    
    if hasattr(schema, 'query_type') and schema.query_type:
        queries = getattr(schema.query_type, 'fields', {}) or getattr(schema.query_type, '_type_definition', {}).get('fields', {})
    
    if hasattr(schema, 'mutation_type') and schema.mutation_type:
        mutations = getattr(schema.mutation_type, 'fields', {}) or getattr(schema.mutation_type, '_type_definition', {}).get('fields', {})

    return JSONResponse({
        "status": "ok",
        "types": num_types,
        "queries": len(queries) if isinstance(queries, (dict, list)) else 0,
        "mutations": len(mutations) if isinstance(mutations, (dict, list)) else 0,
    })


# Wrapper para GraphQL
async def graphql_handler(scope, receive, send):
    """Handler ASGI para GraphQL"""
    try:
        _, graphql_app = _create_graphql_assets()
    except Exception as e:
        # Enviar respuesta de error
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [[b"content-type", b"text/plain"]],
        })
        await send({
            "type": "http.response.body",
            "body": f"Error: {e}\n{traceback.format_exc()}".encode(),
        })
        return
    
    # Inyectar BD en scope
    if scope["type"] == "http":
        scope["state"] = scope.get("state", {})
        scope["state"]["db"] = async_session_maker()
    
    # Delegar a GraphQL
    await graphql_app(scope, receive, send)


# App principal
application = Starlette(
    routes=[
        Route("/", docs_page),
        Route("/health", health),
        Route("/schema.graphql", export_schema),
        Route("/stats", schema_stats),
        Mount("/graphql", app=graphql_handler, name="graphql"),
    ]
)

print("OK Starlette app inicializada")

import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Logger específico para GraphQL
graphql_logger = logging.getLogger('app.graphql')
graphql_logger.setLevel(logging.INFO)
