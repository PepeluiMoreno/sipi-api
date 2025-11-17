from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sipi:sipi@db:5432/sipi")
sync_url = DATABASE_URL.replace("+asyncpg", "")

engine = create_engine(
    sync_url,
    pool_size=5,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=7200,
    echo=False,
)

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
