"""Tie cached narration to the exact journal text it reads.

The weekly rules journal changes as the week goes on, so audio is reused only
while the text, voice and model still match. Rows from before this revision
have no hash and are regenerated on the next listen.
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_narration_text"
down_revision = "0004_ai_opt_in"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("journal_audio")}
    if "text_sha" not in columns:
        op.add_column("journal_audio", sa.Column("text_sha", sa.String(64), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("journal_audio")}
    if "text_sha" in columns:
        op.drop_column("journal_audio", "text_sha")
