"""Enforce one accepted orchestration command per task."""

from collections.abc import Sequence

from alembic import op

revision: str = "0004_one_active_command_per_task"
down_revision: str | None = "0003_command_effects"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX uq_orchestration_one_accepted_per_task
        ON orchestration_commands (task_id)
        WHERE status = 'accepted'
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_orchestration_one_accepted_per_task")
