#!/usr/bin/env python3
import asyncio
import sys
import os

async def wait_for_postgres(host: str, port: int, timeout: int = 30):
    """Espera a que PostgreSQL acepte conexiones usando Python puro"""
    for i in range(timeout):
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=1
            )
            writer.close()
            await writer.wait_closed()
            print(f"✅ PostgreSQL listo en {host}:{port}")
            return True
        except Exception as e:
            print(f"⏳ Esperando PostgreSQL... ({i+1}/{timeout})")
            await asyncio.sleep(1)
    
    print(f"❌ Timeout esperando PostgreSQL", file=sys.stderr)
    return False

if __name__ == "__main__":
    host = sys.argv[1]
    port = int(sys.argv[2])
    timeout = int(sys.argv[3])
    loop = asyncio.get_event_loop()
    ready = loop.run_until_complete(wait_for_postgres(host, port, timeout))
    
    if ready:
        os.execvp(sys.argv[4], sys.argv[4:])
    else:
        sys.exit(1)
