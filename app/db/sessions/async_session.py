
# sipi-core/app/db/sessions/async_session.py
"""
Sistema flexible de conexión a DB para sipi-core
"""
from .manager import AsyncDatabaseManager
from typing import Optional, Dict, Any

class DatabaseRegistry:
    """Registro de múltiples conexiones a DB"""
    _instances: Dict[str, AsyncDatabaseManager] = {}
    _default_key: Optional[str] = None
    
    @classmethod
    def register(
        cls, 
        database_url: str, 
        key: str = "default",
        **kwargs
    ) -> AsyncDatabaseManager:
        """Registrar una nueva conexión"""
        print(f"📥 Registrando conexión '{key}': {database_url[:50]}...")
        
        manager = AsyncDatabaseManager(
            database_url=database_url,
            echo=kwargs.get('echo', False),
            pool_size=kwargs.get('pool_size', 5),
            max_overflow=kwargs.get('max_overflow', 10),
        )
        
        cls._instances[key] = manager
        
        if cls._default_key is None:
            cls._default_key = key
            
        return manager
    
    @classmethod
    def get(cls, key: str = "default") -> AsyncDatabaseManager:
        """Obtener una conexión registrada"""
        if key not in cls._instances:
            raise KeyError(f"Conexión '{key}' no registrada")
        return cls._instances[key]
    
    @classmethod
    def set_default(cls, key: str):
        """Establecer conexión por defecto"""
        if key not in cls._instances:
            raise KeyError(f"Conexión '{key}' no registrada")
        cls._default_key = key
    
    @classmethod
    @property
    def default(cls) -> AsyncDatabaseManager:
        """Obtener la conexión por defecto"""
        if cls._default_key is None:
            raise RuntimeError("No hay conexiones registradas")
        return cls.get(cls._default_key)

# Exportar el registro
db_registry = DatabaseRegistry()

# Funciones de conveniencia
def init_database(database_url: str, **kwargs):
    """Inicializar la base de datos (para compatibilidad)"""
    return db_registry.register(database_url, **kwargs)

def get_db_manager(key: str = "default"):
    """Obtener manager (para compatibilidad)"""
    return db_registry.get(key)

__all__ = ["db_registry", "init_database", "get_db_manager", "AsyncDatabaseManager"]