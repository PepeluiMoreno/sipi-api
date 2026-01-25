#!/usr/bin/env python
"""
Script de inicio para el servidor API GraphQL de SIPI
Lee configuración desde sipi-core/.env
"""
import os
import sys
from pathlib import Path

# Cargar variables de entorno desde sipi-core/.env
env_file = Path(__file__).parent.parent / 'sipi-core' / '.env'

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ.setdefault(key, value)

if __name__ == '__main__':
    # Obtener configuración
    host = os.getenv('API_HOST', 'localhost')
    port = int(os.getenv('API_PORT', '8040'))

    print(f"Iniciando servidor API en {host}:{port}")
    print(f"GraphQL endpoint: http://{host}:{port}/graphql")

    # Importar y ejecutar uvicorn
    import uvicorn

    uvicorn.run(
        "app.graphql.app:application",
        host=host,
        port=port,
        reload=True
    )
