"""Narration usage and a week-keyed audio cache.

Fresh databases already receive these columns from 0002, which creates the
current models. This revision updates a database that migrated earlier.
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_audio"
down_revision = "0002_garden"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "usage_log" not in tables:
        op.create_table(
            "usage_log",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("purpose", sa.String(length=20), nullable=False),
            sa.Column("characters", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("characters >= 0", name="usage_characters_non_negative"),
        )
    if "journals" in tables:
        journal_columns = {column["name"] for column in inspector.get_columns("journals")}
        if "week_start" not in journal_columns:
            op.add_column("journals", sa.Column("week_start", sa.Date(), nullable=True))
    if "journal_audio" in tables:
        audio_columns = {column["name"] for column in inspector.get_columns("journal_audio")}
        if "week_start" not in audio_columns:
            op.drop_table("journal_audio")
            tables.discard("journal_audio")
    if "journal_audio" not in tables:
        op.create_table(
            "journal_audio",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("week_start", sa.Date(), nullable=False),
            sa.Column("voice_id", sa.String(length=80), nullable=False),
            sa.Column("audio", sa.LargeBinary(), nullable=False),
            sa.UniqueConstraint("user_id", "week_start", name="uq_journal_audio_week"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "usage_log" in tables:
        op.drop_table("usage_log")
    if "journals" in tables:
        columns = {column["name"] for column in inspector.get_columns("journals")}
        if "week_start" in columns:
            op.drop_column("journals", "week_start")
