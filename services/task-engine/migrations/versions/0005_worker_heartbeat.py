"""Add durable worker liveness heartbeat."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_worker_heartbeat"
down_revision: str | None = "0004_one_active_command_per_task"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "worker_heartbeats",
        sa.Column("worker_name", sa.String(length=64), primary_key=True),
        sa.Column("worker_id", sa.String(length=128), nullable=True),
        sa.Column("last_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_succeeded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_duration_ms", sa.Integer(), nullable=True),
        sa.Column("last_commands_seen", sa.Integer(), nullable=False),
        sa.Column("last_effects_applied", sa.Integer(), nullable=False),
        sa.Column("last_effects_retried", sa.Integer(), nullable=False),
        sa.Column("last_commands_completed", sa.Integer(), nullable=False),
        sa.Column("last_commands_failed", sa.Integer(), nullable=False),
        sa.Column("last_error_class", sa.String(length=255), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeats")
