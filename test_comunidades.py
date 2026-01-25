import asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text, select
from sipi.db.models.geografia import ComunidadAutonoma
import os

load_dotenv()

async def test():
    url = os.getenv('DATABASE_URL')
    schema = os.getenv('DATABASE_SCHEMA', 'sipi')

    print(f"Testing with schema: {schema}")
    print(f"URL: {url[:50]}...")

    engine = create_async_engine(
        url,
        connect_args={
            'server_settings': {
                'search_path': f'{schema}, public'
            }
        }
    )
    session_maker = async_sessionmaker(engine)

    async with session_maker() as session:
        # Test 1: Raw SQL sin schema
        try:
            result = await session.execute(text('SELECT COUNT(*) FROM comunidades_autonomas'))
            print(f'\n✅ Count with raw SQL (no schema): {result.scalar()}')
        except Exception as e:
            print(f'\n❌ Raw SQL (no schema) failed: {e}')

        # Test 2: Raw SQL con schema
        try:
            result2 = await session.execute(text('SELECT COUNT(*) FROM sipi.comunidades_autonomas'))
            count = result2.scalar()
            print(f'✅ Count with raw SQL (with schema): {count}')

            if count > 0:
                result3 = await session.execute(text('SELECT nombre FROM sipi.comunidades_autonomas LIMIT 3'))
                rows = result3.fetchall()
                print(f'   First 3: {[r[0] for r in rows]}')
        except Exception as e:
            print(f'❌ Raw SQL (with schema) failed: {e}')

        # Test 3: SQLAlchemy ORM
        try:
            stmt = select(ComunidadAutonoma).limit(5)
            result4 = await session.execute(stmt)
            items = result4.scalars().all()
            print(f'\nSQLAlchemy ORM: {len(items)} items')
            if items:
                print(f'   Items: {[item.nombre for item in items]}')
            else:
                print('   WARNING: No items returned!')
        except Exception as e:
            print(f'\nSQLAlchemy ORM failed: {e}')

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test())
