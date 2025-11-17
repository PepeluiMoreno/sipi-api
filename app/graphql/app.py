"""GraphQL ASGI Application"""
from strawberry.asgi import GraphQL
from app.db.sessions.async_session import get_async_db
from app.graphql.schema import create_schema

schema = create_schema()

# ✅ CORRECCIÓN: Manejo correcto del generador async
async def get_context(request):
    db = await anext(get_async_db())
    try:
        return {"db": db}
    finally:
        await db.close()

application = GraphQL(schema, graphiql=True, context_getter=get_context)