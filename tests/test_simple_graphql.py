import strawberry
import asyncio
from sipi.db.sessions.async_session import async_session_maker
from sipi.db.models.geografia import ComunidadAutonoma
from sqlalchemy import select

@strawberry.type
class ComunidadType:
    nombre: str
    codigo_ine: int

@strawberry.type
class Query:
    @strawberry.field
    async def test_comunidades(self) -> list[ComunidadType]:
        async with async_session_maker() as session:
            stmt = select(ComunidadAutonoma).limit(5)
            result = await session.execute(stmt)
            items = result.scalars().all()
            return [ComunidadType(nombre=i.nombre, codigo_ine=i.codigo_ine) for i in items]

schema = strawberry.Schema(query=Query)

# Test it
async def test():
    query = """
    query {
        testComunidades {
            nombre
            codigoIne
        }
    }
    """
    result = await schema.execute(query)
    print(f"Errors: {result.errors}")
    print(f"Data: {result.data}")

if __name__ == "__main__":
    asyncio.run(test())
