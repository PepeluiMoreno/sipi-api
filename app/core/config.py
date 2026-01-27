"""
Configuracion de sipi-api.
Importa desde sipi-core/config.py como fuente central.
"""
import sys
from pathlib import Path

# Agregar sipi-core al path para importar config
sipi_core_path = Path(__file__).parent.parent.parent.parent / "sipi-core"
if sipi_core_path.exists() and str(sipi_core_path) not in sys.path:
    sys.path.insert(0, str(sipi_core_path))

try:
    from config import CONFIG

    # Re-exportar valores desde config central
    DATABASE_URL = CONFIG.DATABASE_URL
    SQLALCHEMY_ECHO = CONFIG.SQLALCHEMY_ECHO
    POOL_SIZE = CONFIG.POOL_SIZE
    POOL_MAX_OVERFLOW = CONFIG.POOL_MAX_OVERFLOW
    POOL_TIMEOUT = CONFIG.POOL_TIMEOUT
    ENVIRONMENT = CONFIG.ENVIRONMENT

except ImportError:
    # Fallback si no encuentra sipi-core
    import os
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sipi:sipi@localhost:5432/sipi")
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
    POOL_SIZE = int(os.getenv("POOL_SIZE", "20"))
    POOL_MAX_OVERFLOW = int(os.getenv("POOL_MAX_OVERFLOW", "10"))
    POOL_TIMEOUT = int(os.getenv("POOL_TIMEOUT", "30"))
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Valores adicionales especificos de la API
POOL_RECYCLE = 3600
GRAPHQL_MAX_DEPTH = 10


class SimpleSettings:
    """Compatibilidad con imports existentes"""
    def __init__(self):
        self.DATABASE_URL = DATABASE_URL
        self.SQLALCHEMY_ECHO = SQLALCHEMY_ECHO
        self.POOL_SIZE = POOL_SIZE
        self.POOL_MAX_OVERFLOW = POOL_MAX_OVERFLOW
        self.POOL_TIMEOUT = POOL_TIMEOUT
        self.POOL_RECYCLE = POOL_RECYCLE
        self.GRAPHQL_MAX_DEPTH = GRAPHQL_MAX_DEPTH
        self.ENVIRONMENT = ENVIRONMENT


settings = SimpleSettings()