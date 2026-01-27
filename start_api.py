#!/usr/bin/env python
"""Inicio del servidor API GraphQL de SIPI"""
import sys
from pathlib import Path

# Agregar directorios al path
root_dir = Path(__file__).parent
sipi_core = root_dir.parent / "sipi-core"
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(sipi_core))

# Cargar configuracion desde sipi-core
from config import CONFIG

if __name__ == "__main__":
    import uvicorn

    host = CONFIG.API_HOST
    port = CONFIG.API_PORT

    print(f"API: http://{host}:{port}/graphql")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=CONFIG.DEBUG,
        reload_excludes=[".venv/*", "ETL/*"],   
        log_level="info"
    )
