# scripts/export_schema.py
"""Exporta el schema GraphQL a archivo SDL"""
from app.graphql.schema import schema

# Exportar schema
schema_str = str(schema)

with open("docs/schema.graphql", "w") as f:
    f.write(schema_str)

print("✅ Schema exportado a docs/schema.graphql")