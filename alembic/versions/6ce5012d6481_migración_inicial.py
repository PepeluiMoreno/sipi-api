"""Migración inicial

Revision ID: 6ce5012d6481
Revises: 
Create Date: 2025-12-12 07:12:59.044800

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from geoalchemy2 import Geometry, Geography

# Importar todos los modelos para que estén en Base.metadata
from sipi.db.models import *
from sipi.db.base import Base

# revision identifiers, used by Alembic.
revision = '6ce5012d6481'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Crear enums primero - usar cadena raw para evitar problemas de escape
    enum_sql1 = r"DO $$ BEGIN CREATE TYPE nivel_proteccion AS ENUM ('nacional', 'autonomico', 'local'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    enum_sql2 = r"DO $$ BEGIN CREATE TYPE tipoidentificacion AS ENUM ('dni', 'nie', 'nif', 'cif', 'pasaporte', 'cif_extranjero', 'otro'); EXCEPTION WHEN duplicate_object THEN null; END $$;"
    
    op.execute(text(enum_sql1))
    op.execute(text(enum_sql2))
    
    # Crear todas las tablas usando SQLAlchemy metadata
    bind = op.get_bind()
    Base.metadata.create_all(bind, checkfirst=True)


def downgrade() -> None:
    # Eliminar todas las tablas
    bind = op.get_bind()
    Base.metadata.drop_all(bind, checkfirst=True)
    
    # Eliminar enums
    op.execute(text("DROP TYPE IF EXISTS nivel_proteccion CASCADE"))
    op.execute(text("DROP TYPE IF EXISTS tipoidentificacion CASCADE"))
