from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from task_engine.enums import FollowupStatus
from task_engine.models import OrchestrationCommand, Task
from task_engine.services.worker_service import CommandWorker


class ProductionCommandWorker(CommandWorker):
    """Production projection rules layered on the generic saga engine."""

    def _apply_local_projection(
        self,
        command_id: str,
        operation: str,
        adapter_result: dict[str, Any],
    ) -> None:
        command = self.session.get(OrchestrationCommand, command_id)
        if command is None:
            return
        metadata_value = command.payload.get("metadata")
        metadata = dict(metadata_value) if isinstance(metadata_value, dict) else {}
        recurring = bool(metadata.get("template_id") and metadata.get("occurrence_key"))
        if not recurring or operation not in {"complete", "wait", "cancel"}:
            super()._apply_local_projection(command_id, operation, adapter_result)
            return

        # A Task Engine Task may represent the persistent recurring canonical action.
        # Resolving one occurrence must therefore never terminally complete/wait/cancel
        # the Task Engine template projection or close unrelated future bindings.
        task = self.session.get(Task, command.task_id)
        if task is None:
            return
        event_id = metadata.get("calendar_event_id")
        now = datetime.now(UTC)
        if event_id:
            for binding in task.calendar_bindings:
                if (
                    binding.event_id == str(event_id)
                    and binding.followup_status == FollowupStatus.PENDING.value
                ):
                    binding.followup_status = FollowupStatus.HANDLED.value
                    binding.followup_handled_at = now
                    binding.updated_at = now
        task.version += 1
        task.updated_at = now
        task.completed_at = None
        self.session.commit()
