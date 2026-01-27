#!/usr/bin/env python3
"""Test script to verify timeline_procesos property works correctly in GraphQL"""

import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker
from sipi.db.models import Inmueble
from app.graphql.schema import create_graphql_types, load_all_models, convert_model_to_graphql
import os
from dotenv import load_dotenv

load_dotenv()

async def test_timeline_property():
    """Test that timeline_procesos property works in GraphQL conversion"""

    # Create async engine
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        return

    # Convert postgresql:// to postgresql+asyncpg://
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Load models and create GraphQL types
        models = load_all_models()
        type_registry = create_graphql_types(models)
        inmueble_type = type_registry.get('Inmueble')

        print("✅ GraphQL type 'Inmueble' loaded")
        print(f"   timeline_procesos field type: {inmueble_type.__annotations__.get('timeline_procesos')}")

        # Fetch one Inmueble with all related data
        stmt = (
            select(Inmueble)
            .options(
                selectinload(Inmueble.inmatriculaciones),
                selectinload(Inmueble.transmisiones),
                selectinload(Inmueble.actuaciones),
            )
            .limit(1)
        )

        result = await session.execute(stmt)
        inmueble = result.scalar_one_or_none()

        if not inmueble:
            print("⚠️  No Inmueble found in database to test")
            return

        print(f"\n✅ Loaded Inmueble: {inmueble.id}")
        print(f"   - Inmatriculaciones: {len(inmueble.inmatriculaciones)}")
        print(f"   - Transmisiones: {len(inmueble.transmisiones)}")
        print(f"   - Actuaciones: {len(inmueble.actuaciones)}")

        # Test property directly
        timeline = inmueble.timeline_procesos
        print(f"\n✅ timeline_procesos property executed")
        print(f"   - Returned {len(timeline)} events")

        if timeline:
            print(f"\n   First event:")
            for key, value in list(timeline[0].items())[:5]:
                print(f"     {key}: {value}")

        # Convert to GraphQL type
        gql_inmueble = convert_model_to_graphql(inmueble, inmueble_type)

        print(f"\n✅ Converted to GraphQL type")
        print(f"   - timelineProcesos field: {type(gql_inmueble.timeline_procesos)}")
        print(f"   - timelineProcesos length: {len(gql_inmueble.timeline_procesos)}")

        if gql_inmueble.timeline_procesos:
            print(f"\n   First GraphQL event:")
            for key, value in list(gql_inmueble.timeline_procesos[0].items())[:5]:
                print(f"     {key}: {value}")

        print("\n✅ SUCCESS: timeline_procesos property works correctly in GraphQL!")

if __name__ == "__main__":
    asyncio.run(test_timeline_property())
