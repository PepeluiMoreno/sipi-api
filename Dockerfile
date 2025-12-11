FROM python:3.11-slim

WORKDIR /code

# Variables de entorno
ENV PYTHONPATH=/code \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación
COPY . .

# Crear directorio para logs
RUN mkdir -p /code/logs

# Establecer permisos de ejecución
RUN chmod +x /code/scripts/entrypoint.sh /code/scripts/wait-for-db.sh

# Puerto de la aplicación
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8040/health || exit 1

ENTRYPOINT ["/code/scripts/entrypoint.sh"]
