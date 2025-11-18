"""SQLAlchemy Async Session Factory"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.POOL_MAX_OVERFLOW,
    pool_timeout=settings.POOL_TIMEOUT,
    pool_pre_ping=True,
    pool_recycle=settings.POOL_RECYCLE,
    echo=settings.SQLALCHEMY_ECHO,
)

# NOMBRE CORRECTO que app.py espera
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

AsyncSessionLocal = async_session_maker  # Alias opcional

async def get_async_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()