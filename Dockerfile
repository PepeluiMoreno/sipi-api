FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .
COPY entrypoint.sh .          
COPY wait-for-db.sh . 

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN chmod +x /app/entrypoint.sh /app/wait-for-db.sh

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://${GRAPHQL_HOST:-0.0.0.0}:${GRAPHQL_PORT:-8000}/graphql || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
