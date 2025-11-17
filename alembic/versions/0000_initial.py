# alembic/versions/0000_initial.py
"""initial schema: create inmuebles (minimal)

Revision ID: 0000_initial
Revises: 
Create Date: 2025-11-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0000_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "inmuebles",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text, nullable=True),
        sa.Column("direccion", sa.String(255), nullable=True),
        sa.Column("latitud", sa.Float, nullable=True),
        sa.Column("longitud", sa.Float, nullable=True),
    )

def downgrade():
    op.drop_table("inmuebles")
