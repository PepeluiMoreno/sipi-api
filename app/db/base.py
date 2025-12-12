# app/db/base.py
import os
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData

# ✅ Schema configurable via variable de entorno
DB_SCHEMA = os.getenv("DB_SCHEMA", "sipi")

# ✅ Configurar metadata con schema por defecto
metadata = MetaData(schema=DB_SCHEMA)

# ✅ Base declarativa con el metadata personalizado
Base = declarative_base(metadata=metadata)

# Hacer que el schema sea accesible
Base.schema = DB_SCHEMA