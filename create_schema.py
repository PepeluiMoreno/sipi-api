import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

async def create_schemas():
    DATABASE_URL = os.getenv('DATABASE_URL')
    engine = create_async_engine(DATABASE_URL)

    # Intentar habilitar PostGIS en una transacción separada
    async with engine.connect() as conn:
        try:
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS postgis'))
            await conn.commit()
            print('PostGIS extension enabled')
        except Exception as e:
            await conn.rollback()
            print(f'PostGIS extension not available (continuing without it)')

    # Crear esquemas en una transacción separada
    async with engine.begin() as conn:
        await conn.execute(text('CREATE SCHEMA IF NOT EXISTS sipi'))
        await conn.execute(text('CREATE SCHEMA IF NOT EXISTS portals'))
        print('Schemas created: sipi, portals')

    await engine.dispose()

asyncio.run(create_schemas())
