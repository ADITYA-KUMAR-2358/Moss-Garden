"""Per-gardener AI opt-in. Off for everyone until they turn it on.

Fresh databases already receive this column from 0002, which creates the
current models. This revision updates a database that migrated earlier.
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_ai_opt_in"
down_revision = "0003_audio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "ai_opt_in" not in columns:
        op.add_column(
            "users",
            sa.Column("ai_opt_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "ai_opt_in" in columns:
        op.drop_column("users", "ai_opt_in")
