import asyncio
import asyncpg
import sys
import os

async def test_aiven_connection():
    # URL de Aiven proporcionada por entorno
    url = os.getenv("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_URL not set")
        return

    # asyncpg requiere postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[11:]

    host = url.split('@')[1] if '@' in url else 'unknown'
    print(f"Connecting to: {host}") # Print host only for security
    try:
        conn = await asyncio.wait_for(
            asyncpg.connect(url), 
            timeout=15
        )
        print("SUCCESS: Connected to Aiven.")
        
        version = await conn.fetchval("SELECT version()")
        print(f"Version: {version}")
        
        await conn.close()
    except Exception as e:
        print(f"ERROR connecting to Aiven: {type(e).__name__}: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_aiven_connection())
