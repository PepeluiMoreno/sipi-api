import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text, inspect

# URL proporcionada por el usuario (convertida a asyncpg)
LEGACY_URL = "postgresql+asyncpg://avnadmin:AVNS_wFKVpyYaBMZRRMDiFjz@pepelu-postgresql-joseluis-moreno.h.aivencloud.com:17113/defaultdb?ssl=require"

async def inspect_db():
    print(f"🔌 Conectando a: {LEGACY_URL.split('@')[1]}...") # Ocultar credenciales en log
    
    try:
        engine = create_async_engine(LEGACY_URL)
        
        async with engine.connect() as conn:
            # Listar tablas públicas
            result = await conn.execute(text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            ))
            tables = result.scalars().all()
            
            print(f"✅ Conexión exitosa. Encontradas {len(tables)} tablas publicas:\n")
            
            for table in tables:
                print(f"📦 Tabla: {table}")
                # Obtener columnas
                cols_res = await conn.execute(text(
                    f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}'"
                ))
                cols = cols_res.fetchall()
                for col in cols:
                    print(f"   - {col[0]} ({col[1]})")
                
                # Count
                count_res = await conn.execute(text(f"SELECT COUNT(*) FROM public.{table}"))
                count = count_res.scalar()
                print(f"   📊 Registros: {count}\n")
                
    except Exception as e:
        print(f"❌ Error conectando: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_db())
