"""
Direct test of resolver logic to debug empty results
"""
import asyncio
from sipi.db.sessions.async_session import async_session_maker
from sipi.db.models.geografia import ComunidadAutonoma
from sqlalchemy import select

async def test_direct_query():
    print("Testing direct SQLAlchemy query...")

    async with async_session_maker() as session:
        # This is what the resolver should be doing
        stmt = select(ComunidadAutonoma).limit(50)
        print(f"Statement: {stmt}")

        result = await session.execute(stmt)
        instances = result.scalars().all()

        print(f"Found {len(instances)} records")
        if instances:
            for inst in instances[:3]:
                print(f"  - {inst.nombre} ({inst.codigo_ine})")
        else:
            print("  ERROR: No instances returned!")

            # Debug: Try raw SQL
            from sqlalchemy import text
            result2 = await session.execute(text("SELECT COUNT(*) FROM comunidades_autonomas"))
            count = result2.scalar()
            print(f"  Raw SQL count: {count}")

if __name__ == "__main__":
    asyncio.run(test_direct_query())
