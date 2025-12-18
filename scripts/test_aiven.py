import asyncio
import asyncpg
import sys
import os

async def test_aiven_connection():
    # URL de Aiven proporcionada por el usuario
    url = "postgres://avnadmin:AVNS_wFKVpyYaBMZRRMDiFjz@pepelu-postgresql-joseluis-moreno.h.aivencloud.com:17113/defaultdb?sslmode=require"
    
    # asyncpg requiere postgresql://
    if url.startswith("postgres://"):
        url = "postgresql://" + url[11:]

    print(f"Connecting to: {url.split('@')[1]}") # Print host only for security
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
