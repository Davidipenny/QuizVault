"""Store import row errors independently.

Revision ID: 0002
"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "import_errors" not in inspector.get_table_names():
        op.create_table(
            "import_errors",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("job_id", sa.String(36), sa.ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False),
            sa.Column("row_number", sa.Integer(), nullable=False),
            sa.Column("messages", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_import_errors_job_id", "import_errors", ["job_id"])


def downgrade():
    op.drop_table("import_errors")
