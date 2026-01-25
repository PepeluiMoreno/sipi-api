"""
Test script to verify search_path configuration in asyncpg
"""
import asyncio
from dotenv import load_dotenv
from sipi.db.sessions.async_session import async_session_maker
from sqlalchemy import text

load_dotenv()

async def test_search_path():
    print("=" * 60)
    print("Testing search_path configuration")
    print("=" * 60)

    async with async_session_maker() as session:
        # Test 1: Check current search_path
        result = await session.execute(text("SHOW search_path"))
        current_path = result.scalar()
        print(f"\n[OK] Current search_path: {current_path}")

        # Test 2: Try query without schema prefix
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM comunidades_autonomas"))
            count = result.scalar()
            print(f"[OK] Query without schema prefix succeeded: {count} records")
        except Exception as e:
            print(f"[FAIL] Query without schema prefix failed: {e}")

        # Test 3: Try query with schema prefix
        try:
            result = await session.execute(text("SELECT COUNT(*) FROM sipi.comunidades_autonomas"))
            count = result.scalar()
            print(f"[OK] Query with schema prefix succeeded: {count} records")
        except Exception as e:
            print(f"[FAIL] Query with schema prefix failed: {e}")

        # Test 4: Try SQLAlchemy ORM query
        try:
            from sipi.db.models.geografia import ComunidadAutonoma
            from sqlalchemy import select

            stmt = select(ComunidadAutonoma)
            result = await session.execute(stmt)
            items = result.scalars().all()
            print(f"[OK] SQLAlchemy ORM query succeeded: {len(items)} records")
            if items:
                print(f"  First item: {items[0].nombre}")
        except Exception as e:
            print(f"[FAIL] SQLAlchemy ORM query failed: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_path())
