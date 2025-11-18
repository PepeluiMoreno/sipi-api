"""Simple Configuration - SIN Pydantic"""
import os

def get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)

# Database
DATABASE_URL = get_env("DATABASE_URL", "postgresql+asyncpg://sipi:sipi@db:5432/sipi")

# SQLAlchemy (aplica a sync y async)
SQLALCHEMY_ECHO = get_env("SQLALCHEMY_ECHO", "false").lower() == "true"
POOL_SIZE = int(get_env("POOL_SIZE", "20"))
POOL_MAX_OVERFLOW = int(get_env("POOL_MAX_OVERFLOW", "10"))
POOL_TIMEOUT = int(get_env("POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(get_env("POOL_RECYCLE", "3600"))

# GraphQL
GRAPHQL_MAX_DEPTH = int(get_env("GRAPHQL_MAX_DEPTH", "10"))

# Environment
ENVIRONMENT = get_env("ENVIRONMENT", "development")

# ✅ ESTA ES LA LÍNEA CLAVE QUE FALTABA
# Simula el patrón de Pydantic settings para compatibilidad con los imports
class SimpleSettings:
    def __init__(self):
        self.DATABASE_URL = DATABASE_URL
        self.SQLALCHEMY_ECHO = SQLALCHEMY_ECHO
        self.POOL_SIZE = POOL_SIZE
        self.POOL_MAX_OVERFLOW = POOL_MAX_OVERFLOW
        self.POOL_TIMEOUT = POOL_TIMEOUT
        self.POOL_RECYCLE = POOL_RECYCLE
        self.GRAPHQL_MAX_DEPTH = GRAPHQL_MAX_DEPTH
        self.ENVIRONMENT = ENVIRONMENT

# ✅ EXPORTA LA INSTANCIA GLOBAL 'settings'
settings = SimpleSettings()