#!/bin/bash
set -e

host="$1"
port="${2:-5432}"
timeout="${3:-30}"
shift 3

echo "⏳ Esperando PostgreSQL en $host:$port..."
for i in $(seq 1 "$timeout"); do
    if nc -z "$host" "$port"; then
        echo "✅ PostgreSQL listo!"
        exec "$@"
    fi
    sleep 1
done

echo "❌ Timeout esperando PostgreSQL" >&2
exit 1
