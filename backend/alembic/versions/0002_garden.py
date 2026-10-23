"""Create the garden tables from the SQLAlchemy models."""

from app.models import Base

revision = "0002_garden"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op_bind())


def op_bind():
    from alembic import op

    return op.get_bind()
