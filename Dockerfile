FROM python:3.11-slim

# ✅ Usar /code en lugar de /app
WORKDIR /code

ENV PYTHONPATH=/code
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# gcc para compilar dependencias + curl para healthcheck
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias primero
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . . 

RUN chmod +x /code/entrypoint.sh /code/wait-for-db.sh
EXPOSE ${GRAPHQL_PORT:-8000}


HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://${GRAPHQL_HOST:-0.0.0.0}:${GRAPHQL_PORT:-8000}/graphql || exit 1

ENTRYPOINT ["/code/entrypoint.sh"]
