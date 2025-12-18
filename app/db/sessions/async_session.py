"""
SQLAlchemy Async Session Wrapper using SIPI-CORE Manager
Adapts the core manager to the API specific configuration (settings).
"""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings

# Importar el manager del core
# Asumimos que sipi-core está instalado como package 'sipi'
from sipi.db.sessions.manager import AsyncDatabaseManager

# Instancia global del manager configurada con settings de la API
db_manager = AsyncDatabaseManager(
    database_url=settings.DATABASE_URL,
    pool_size=settings.POOL_SIZE,
    max_overflow=settings.POOL_MAX_OVERFLOW,
    pool_timeout=settings.POOL_TIMEOUT,
    pool_recycle=settings.POOL_RECYCLE,
    echo=settings.SQLALCHEMY_ECHO,
)

# Mantener compatibilidad con imports existentes en app.py
# app.py espera: async_session_maker (o similar) y get_async_db

async_session_maker = db_manager.session_maker

async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injection wrapper"""
    async with db_manager.get_session() as session:
        yield session

# Función para cerrar conexión al apagar app
async def close_db_connection():
    await db_manager.close()