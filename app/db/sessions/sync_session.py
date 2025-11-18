from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings  # ✅ Usa configuración centralizada

# Convertir URL async a sync (elimina +asyncpg)
sync_url = settings.DATABASE_URL.replace("+asyncpg", "")

engine = create_engine(
    sync_url,
    pool_size=settings.POOL_SIZE,              # ✅ Config驱动
    max_overflow=settings.POOL_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_timeout=settings.POOL_TIMEOUT,
    pool_recycle=settings.POOL_RECYCLE,
    echo=settings.SQLALCHEMY_ECHO,
)

# Factory de sesiones sincronas
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

def get_sync_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()