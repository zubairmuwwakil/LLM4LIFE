"""Add durable command effect saga journal."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_command_effects"
down_revision: str | None = "0002_orchestration_commands"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "command_effects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "command_id",
            sa.String(length=36),
            sa.ForeignKey("orchestration_commands.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("effect_key", sa.String(length=255), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("target", sa.String(length=32), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("request_payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_owner", sa.String(length=128), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("effect_key", name="uq_command_effect_key"),
        sa.UniqueConstraint("command_id", "ordinal", name="uq_command_effect_ordinal"),
    )
    op.create_index(
        "ix_command_effects_runnable",
        "command_effects",
        ["status", "next_attempt_at", "lease_until", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_command_effects_runnable", table_name="command_effects")
    op.drop_table("command_effects")
