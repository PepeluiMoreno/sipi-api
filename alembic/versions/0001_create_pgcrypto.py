# alembic/versions/0001_create_pgcrypto.py
"""enable pgcrypto extension

Revision ID: 0001_create_pgcrypto
Revises: 0000_initial
Create Date: 2025-11-12 00:00:01.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_create_pgcrypto"
down_revision = "0000_initial"
branch_labels = None
depends_on = None

def upgrade():
    # only works on Postgres; safe-guard: use raw SQL
    conn = op.get_bind()
    try:
        conn.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pgcrypto;"))
    except Exception:
        # ignore on non-postgres
        pass

def downgrade():
    conn = op.get_bind()
    try:
        conn.execute(sa.text("DROP EXTENSION IF EXISTS pgcrypto;"))
    except Exception:
        pass
