"""GraphQL ASGI Application"""
from typing import Dict, Any
from strawberry.asgi import GraphQL
from app.db.sessions.async_session import async_session_maker
from app.graphql.schema import create_schema

schema = create_schema()

# ✅ CORREGIDO: Sessions por request, ciclo de vida manejado por Strawberry
async def get_context(request) -> Dict[str, Any]:
    return {"db": async_session_maker()}

application = GraphQL(schema, graphiql=True, context_getter=get_context)