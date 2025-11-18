# app/graphql/app.py - VERSIÓN COMPATIBLE

from strawberry.asgi import GraphQL
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse, JSONResponse, HTMLResponse
from starlette.routing import Route
from app.db.sessions.async_session import async_session_maker
from app.graphql.schema import schema

# ✅ Contexto como clase
class Context:
    def __init__(self):
        self.db = async_session_maker()

# ✅ GraphQL sin context_getter
graphql_app = GraphQL(schema, graphiql=True)

# Endpoints de documentación
async def export_schema(request):
    return PlainTextResponse(str(schema))

async def schema_stats(request):
    types = schema.type_map
    queries = schema.query_type.fields if schema.query_type else {}
    mutations = schema.mutation_type.fields if schema.mutation_type else {}
    
    return JSONResponse({
        "types": len([t for t in types if not t.startswith('__')]),
        "queries": len(queries),
        "mutations": len(mutations),
    })

async def docs_page(request):
    return HTMLResponse("""
    <html>
    <head><title>SIPI GraphQL API</title></head>
    <body style="font-family: sans-serif; max-width: 800px; margin: 50px auto;">
        <h1>🏛️ SIPI GraphQL API</h1>
        <ul>
            <li><a href="/graphql">🌐 GraphiQL (Explorador interactivo)</a></li>
            <li><a href="/schema.graphql">📄 Schema SDL</a></li>
        </ul>
    </body>
    </html>
    """)

# ✅ App con múltiples rutas
application = Starlette(
    routes=[
        Route("/", docs_page),
        Route("/graphql", graphql_app),
        Route("/schema.graphql", export_schema),
        Route("/stats", schema_stats),
    ]
)