from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from task_engine.enums import (
    ExecutionPolicy,
    OrchestrationCommandStatus,
    OrchestrationCommandType,
    TaskStatus,
)
from task_engine.models import OrchestrationCommand, OutboxEvent, Task
from task_engine.schemas import OrchestrationCommandComplete, OrchestrationCommandSubmit
from task_engine.services.task_service import ConflictError, NotFoundError


class CommandService:
    """Durable, idempotent handoff between AI reasoning and deterministic workers.

    The AI chooses *what should happen*. This service persists that decision before any
    Calendar/canonical-state side effect, publishes exactly one outbox request, and
    provides an idempotent completion callback for the worker that performs the side effect.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def submit(self, task_id: str, data: OrchestrationCommandSubmit) -> OrchestrationCommand:
        existing = self.session.scalar(
            select(OrchestrationCommand).where(
                OrchestrationCommand.command_key == data.command_key
            )
        )
        normalized_payload = self._normalized_payload(data)
        if existing is not None:
            self._assert_same_command(existing, task_id, data, normalized_payload)
            return existing

        task = self.session.get(Task, task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        if data.expected_task_version is not None and data.expected_task_version != task.version:
            raise ConflictError(
                f"Version mismatch: expected {data.expected_task_version}, current {task.version}"
            )
        if task.status in {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value}:
            raise ConflictError("Terminal tasks cannot accept new orchestration commands")
        if (
            data.command_type == OrchestrationCommandType.RESCHEDULE
            and task.execution_policy == ExecutionPolicy.FIXED.value
        ):
            raise ConflictError("Fixed tasks cannot be rescheduled by the orchestration control plane")

        active = self.session.scalar(
            select(OrchestrationCommand).where(
                OrchestrationCommand.task_id == task.id,
                OrchestrationCommand.status == OrchestrationCommandStatus.ACCEPTED.value,
            )
        )
        if active is not None:
            raise ConflictError(
                f"Task already has accepted command {active.command_key}; resolve or fail it before issuing another"
            )

        command = OrchestrationCommand(
            task_id=task.id,
            command_key=data.command_key,
            command_type=data.command_type.value,
            expected_task_version=data.expected_task_version,
            requested_by=data.requested_by,
            payload=normalized_payload,
        )
        self.session.add(command)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(
                "Orchestration command conflicts with an existing command or active task decision"
            ) from exc

        self._emit_requested(task, command)
        self.session.commit()
        self.session.refresh(command)
        return command

    def get(self, command_id: str) -> OrchestrationCommand:
        command = self.session.get(OrchestrationCommand, command_id)
        if command is None:
            raise NotFoundError(f"Orchestration command {command_id} not found")
        return command

    def complete(
        self,
        command_id: str,
        data: OrchestrationCommandComplete,
    ) -> OrchestrationCommand:
        command = self.get(command_id)
        target_status = (
            OrchestrationCommandStatus.COMPLETED.value
            if data.success
            else OrchestrationCommandStatus.FAILED.value
        )
        normalized_result = data.model_dump(mode="json")["result"]

        if command.status != OrchestrationCommandStatus.ACCEPTED.value:
            if (
                command.status == target_status
                and (command.result_payload or {}) == normalized_result
                and command.failure_reason == data.error
            ):
                return command
            raise ConflictError(
                f"Command already finalized as {command.status}; conflicting completion rejected"
            )

        command.status = target_status
        command.result_payload = normalized_result
        command.failure_reason = data.error
        command.completed_at = datetime.now(UTC)
        self.session.flush()

        task = self.session.get(Task, command.task_id)
        if task is None:
            raise NotFoundError(f"Task {command.task_id} not found")
        event_type = (
            "orchestration.command.completed"
            if data.success
            else "orchestration.command.failed"
        )
        self.session.add(
            OutboxEvent(
                event_type=event_type,
                aggregate_type="orchestration_command",
                aggregate_id=command.id,
                idempotency_key=f"command:{command.command_key}:{command.status}",
                payload={
                    "command_id": command.id,
                    "command_key": command.command_key,
                    "command_type": command.command_type,
                    "task_id": task.id,
                    "source_system": task.source_system,
                    "source_id": task.source_id,
                    "result": normalized_result,
                    "error": data.error,
                },
            )
        )
        self.session.commit()
        self.session.refresh(command)
        return command

    @staticmethod
    def _normalized_payload(data: OrchestrationCommandSubmit) -> dict[str, object]:
        dumped = data.model_dump(
            mode="json",
            exclude={"command_key", "command_type", "expected_task_version", "requested_by"},
        )
        return dict(dumped)

    @staticmethod
    def _assert_same_command(
        existing: OrchestrationCommand,
        task_id: str,
        data: OrchestrationCommandSubmit,
        normalized_payload: dict[str, object],
    ) -> None:
        if (
            existing.task_id != task_id
            or existing.command_type != data.command_type.value
            or existing.requested_by != data.requested_by
            or existing.payload != normalized_payload
        ):
            raise ConflictError(
                "command_key was already used for a different orchestration decision"
            )

    def _emit_requested(self, task: Task, command: OrchestrationCommand) -> None:
        self.session.add(
            OutboxEvent(
                event_type=f"orchestration.{command.command_type}.requested",
                aggregate_type="orchestration_command",
                aggregate_id=command.id,
                idempotency_key=f"command:{command.command_key}:requested",
                payload={
                    "command_id": command.id,
                    "command_key": command.command_key,
                    "command_type": command.command_type,
                    "task_id": task.id,
                    "source_system": task.source_system,
                    "source_id": task.source_id,
                    "task_version": task.version,
                    "payload": command.payload,
                },
            )
        )
