import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

# Import Base and models at module level
from sipi.db.base import Base
import sipi.db.models  # noqa

load_dotenv()

async def test_migration():
    DATABASE_URL = os.getenv('DATABASE_URL')
    print(f"Connecting to: {DATABASE_URL[:50]}...")
    engine = create_async_engine(DATABASE_URL, echo=False)  # Disable echo for cleaner output

    async with engine.begin() as conn:
        print("Enabling extensions...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        print("[OK] Extensions enabled")

        print("Creating schemas...")
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS sipi"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS portals"))
        print("[OK] Schemas created")

        print("Setting search_path...")
        await conn.execute(text("SET search_path TO sipi, portals, public"))
        print("[OK] Search path set")

        print("Creating ENUMs...")
        await conn.execute(text(r"DO $$ BEGIN CREATE TYPE nivel_proteccion AS ENUM ('nacional', 'autonomico', 'local'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
        await conn.execute(text(r"DO $$ BEGIN CREATE TYPE tipoidentificacion AS ENUM ('dni', 'nie', 'nif', 'cif', 'pasaporte', 'cif_extranjero', 'otro'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
        await conn.execute(text(r"DO $$ BEGIN CREATE TYPE estadociclovida AS ENUM ('inmatriculado', 'en_venta', 'vendido', 'cambio_de_uso'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
        await conn.execute(text(r"DO $$ BEGIN CREATE TYPE geoquality AS ENUM ('manual', 'auto', 'missing'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
        await conn.execute(text(r"DO $$ BEGIN CREATE TYPE lifecycleeventtype AS ENUM ('alta_inmatriculacion', 'puesta_en_venta', 'vendido', 'cambio_de_uso', 'rehabilitacion', 'rehabilitacion_subvencionada', 'declaracion_bic', 'cambio_visitabilidad'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
        print("[OK] All ENUMs created")

        print("\nNow attempting to create tables with Base.metadata.create_all()...")

        def run_create_all(connection):
            print(f"  Found {len(Base.metadata.sorted_tables)} tables in metadata")
            Base.metadata.create_all(connection, checkfirst=True)

        await conn.run_sync(run_create_all)
        print("[OK] Tables created successfully!")

    await engine.dispose()
    print("\n[DONE] Migration test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_migration())
