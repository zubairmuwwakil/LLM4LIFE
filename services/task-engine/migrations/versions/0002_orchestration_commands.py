"""Add durable orchestration command handoff ledger."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_orchestration_commands"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orchestration_commands",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "task_id",
            sa.String(length=36),
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("command_key", sa.String(length=255), nullable=False),
        sa.Column("command_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("expected_task_version", sa.Integer(), nullable=True),
        sa.Column("requested_by", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("command_key", name="uq_orchestration_command_key"),
    )
    op.create_index(
        "ix_orchestration_commands_status_created_at",
        "orchestration_commands",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_orchestration_commands_task_id_created_at",
        "orchestration_commands",
        ["task_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orchestration_commands_task_id_created_at",
        table_name="orchestration_commands",
    )
    op.drop_index(
        "ix_orchestration_commands_status_created_at",
        table_name="orchestration_commands",
    )
    op.drop_table("orchestration_commands")
