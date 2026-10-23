"""Baseline revision.

Domain tables are intentionally absent. The data model document does not
exist yet, so this revision only proves the migration chain can run.
"""

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
