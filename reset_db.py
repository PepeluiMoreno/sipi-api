"""
Script para resetear completamente la base de datos SIPI.
ADVERTENCIA: Esto eliminara TODOS los datos en los schemas sipi y portals.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

async def reset_database():
    DATABASE_URL = os.getenv('DATABASE_URL')
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        print("Eliminando schemas...")
        await conn.execute(text("DROP SCHEMA IF EXISTS sipi CASCADE"))
        await conn.execute(text("DROP SCHEMA IF EXISTS portals CASCADE"))
        print("[OK] Schemas eliminados")

        print("Eliminando tipos ENUM...")
        await conn.execute(text("DROP TYPE IF EXISTS nivel_proteccion CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS tipoidentificacion CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS estadociclovida CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS geoquality CASCADE"))
        await conn.execute(text("DROP TYPE IF EXISTS lifecycleeventtype CASCADE"))
        print("[OK] ENUMs eliminados")

        print("Eliminando tabla de versiones de Alembic...")
        await conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        print("[OK] Alembic version eliminado")

        print("\n[DONE] Base de datos resetada completamente")
        print("Ahora puedes ejecutar: alembic upgrade head")

    await engine.dispose()

if __name__ == "__main__":
    print("ADVERTENCIA: Esto eliminara TODOS los datos en schemas sipi y portals")
    confirm = input("Continuar? (escribe 'SI' para confirmar): ")
    if confirm == "SI":
        asyncio.run(reset_database())
    else:
        print("[CANCELADO] Operacion cancelada")
