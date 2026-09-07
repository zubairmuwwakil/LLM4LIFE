from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from task_engine.config import Settings
from task_engine.enums import (
    CommandEffectStatus,
    FollowupStatus,
    OrchestrationCommandStatus,
    TaskStatus,
)
from task_engine.models import CalendarBinding, CommandEffect, OrchestrationCommand, Task
from task_engine.schemas import OrchestrationCommandComplete, WorkerRunResult
from task_engine.services.command_service import CommandService
from task_engine.worker.adapters import (
    EffectAdapter,
    EffectEnvelope,
    PermanentEffectError,
    RetryableEffectError,
)


EFFECT_PLANS: dict[str, tuple[tuple[str, str], ...]] = {
    "complete": (("canonical", "complete"), ("calendar", "mark_completed")),
    "reschedule": (("calendar", "ensure_execution"), ("canonical", "reschedule")),
    "wait": (("canonical", "wait"), ("calendar", "mark_waiting")),
    "cancel": (("canonical", "cancel"), ("calendar", "mark_cancelled")),
    "defer": (("canonical", "defer"), ("calendar", "mark_deferred")),
    "status_check": (("calendar", "ensure_status_check"), ("canonical", "bind_status_check")),
}


class CommandWorker:
    """Runs accepted orchestration commands as ordered, checkpointed sagas.

    External delivery is at-least-once. Each adapter must therefore make its operation
    idempotent using `effect_key`/`command_key`. The effect journal ensures a completed
    step is never intentionally re-run after its checkpoint is durable.
    """

    def __init__(
        self,
        session: Session,
        settings: Settings,
        adapters: dict[str, EffectAdapter],
    ) -> None:
        self.session = session
        self.settings = settings
        self.adapters = adapters

    def run(self, *, worker_id: str | None = None, max_commands: int = 20) -> WorkerRunResult:
        worker_id = worker_id or f"task-engine:{uuid.uuid4()}"
        stats = {
            "commands_seen": 0,
            "effects_applied": 0,
            "effects_retried": 0,
            "commands_completed": 0,
            "commands_failed": 0,
        }
        command_ids = list(
            self.session.scalars(
                select(OrchestrationCommand.id)
                .where(OrchestrationCommand.status == OrchestrationCommandStatus.ACCEPTED.value)
                .order_by(OrchestrationCommand.created_at.asc())
                .limit(max_commands)
            )
        )
        for command_id in command_ids:
            stats["commands_seen"] += 1
            outcome = self._run_command(command_id, worker_id)
            stats["effects_applied"] += outcome["effects_applied"]
            stats["effects_retried"] += outcome["effects_retried"]
            stats["commands_completed"] += int(outcome["completed"])
            stats["commands_failed"] += int(outcome["failed"])
        return WorkerRunResult(worker_id=worker_id, **stats)

    def effects_for_command(self, command_id: str) -> list[CommandEffect]:
        return list(
            self.session.scalars(
                select(CommandEffect)
                .where(CommandEffect.command_id == command_id)
                .order_by(CommandEffect.ordinal.asc())
            )
        )

    def ensure_plan(self, command: OrchestrationCommand) -> list[CommandEffect]:
        plan = EFFECT_PLANS.get(command.command_type)
        if plan is None:
            raise PermanentEffectError(f"No effect plan for command type {command.command_type}")
        existing = self.effects_for_command(command.id)
        if existing:
            actual = tuple((effect.target, effect.operation) for effect in existing)
            if actual != plan:
                raise PermanentEffectError(
                    f"Persisted effect plan differs from protocol for command {command.command_key}"
                )
            return existing
        for ordinal, (target, operation) in enumerate(plan, start=1):
            self.session.add(
                CommandEffect(
                    command_id=command.id,
                    effect_key=f"command:{command.command_key}:effect:{ordinal}:{target}:{operation}",
                    ordinal=ordinal,
                    target=target,
                    operation=operation,
                    request_payload={},
                )
            )
        self.session.commit()
        return self.effects_for_command(command.id)

    def _run_command(self, command_id: str, worker_id: str) -> dict[str, int | bool]:
        result: dict[str, int | bool] = {
            "effects_applied": 0,
            "effects_retried": 0,
            "completed": False,
            "failed": False,
        }
        command = self.session.get(OrchestrationCommand, command_id)
        if command is None or command.status != OrchestrationCommandStatus.ACCEPTED.value:
            return result
        try:
            effects = self.ensure_plan(command)
        except PermanentEffectError as exc:
            self._fail_command(command, str(exc))
            result["failed"] = True
            return result

        for effect in effects:
            self.session.refresh(effect)
            if effect.status == CommandEffectStatus.COMPLETED.value:
                continue
            if effect.status == CommandEffectStatus.FAILED.value:
                self._fail_command(command, effect.last_error or "terminal effect failure")
                result["failed"] = True
                return result
            if not self._claim_effect(effect.id, worker_id):
                return result
            self.session.refresh(effect)
            try:
                envelope = self._envelope(command, effect)
                adapter = self.adapters.get(effect.target)
                if adapter is None:
                    raise PermanentEffectError(f"No adapter configured for target {effect.target}")
                adapter_result = adapter.apply(envelope)
                self._complete_effect(effect.id, worker_id, adapter_result)
                self._apply_local_projection(command.id, effect.operation, adapter_result)
                result["effects_applied"] = int(result["effects_applied"]) + 1
            except RetryableEffectError as exc:
                retrying = self._retry_effect(effect.id, worker_id, str(exc))
                result["effects_retried"] = int(result["effects_retried"]) + int(retrying)
                if not retrying:
                    self._fail_command(command, str(exc))
                    result["failed"] = True
                return result
            except PermanentEffectError as exc:
                self._terminal_effect_failure(effect.id, worker_id, str(exc))
                self._fail_command(command, str(exc))
                result["failed"] = True
                return result
            except Exception as exc:  # defensive classification: unknown failures retry first
                retrying = self._retry_effect(
                    effect.id, worker_id, f"unclassified {type(exc).__name__}: {exc}"
                )
                result["effects_retried"] = int(result["effects_retried"]) + int(retrying)
                if not retrying:
                    self._fail_command(command, str(exc))
                    result["failed"] = True
                return result

        effects = self.effects_for_command(command.id)
        if effects and all(e.status == CommandEffectStatus.COMPLETED.value for e in effects):
            completion = {
                f"{effect.target}.{effect.operation}": effect.result_payload or {}
                for effect in effects
            }
            CommandService(self.session).complete(
                command.id,
                OrchestrationCommandComplete(success=True, result={"effects": completion}),
            )
            result["completed"] = True
        return result

    def _claim_effect(self, effect_id: str, worker_id: str) -> bool:
        now = datetime.now(UTC)
        lease_until = now + timedelta(seconds=self.settings.worker_lease_seconds)
        runnable_status = CommandEffect.status.in_(
            [CommandEffectStatus.PENDING.value, CommandEffectStatus.RETRYABLE.value]
        )
        expired_running = and_(
            CommandEffect.status == CommandEffectStatus.RUNNING.value,
            or_(CommandEffect.lease_until.is_(None), CommandEffect.lease_until < now),
        )
        stmt = (
            update(CommandEffect)
            .where(
                CommandEffect.id == effect_id,
                or_(runnable_status, expired_running),
                or_(CommandEffect.next_attempt_at.is_(None), CommandEffect.next_attempt_at <= now),
            )
            .values(
                status=CommandEffectStatus.RUNNING.value,
                lease_owner=worker_id,
                lease_until=lease_until,
                attempt_count=CommandEffect.attempt_count + 1,
                updated_at=now,
            )
        )
        outcome = self.session.execute(stmt)
        self.session.commit()
        return bool(outcome.rowcount)

    def _envelope(self, command: OrchestrationCommand, effect: CommandEffect) -> EffectEnvelope:
        task = self.session.get(Task, command.task_id)
        if task is None:
            raise PermanentEffectError(f"Task {command.task_id} not found")
        prior = {
            f"{item.target}.{item.operation}": dict(item.result_payload or {})
            for item in self.effects_for_command(command.id)
            if item.ordinal < effect.ordinal and item.status == CommandEffectStatus.COMPLETED.value
        }
        bindings = tuple(
            {
                "id": item.id,
                "provider": item.provider,
                "calendar_id": item.calendar_id,
                "event_id": item.event_id,
                "scheduled_start": item.scheduled_start.isoformat(),
                "scheduled_end": item.scheduled_end.isoformat(),
                "followup_status": item.followup_status,
            }
            for item in task.calendar_bindings
        )
        return EffectEnvelope(
            effect_id=effect.id,
            effect_key=effect.effect_key,
            target=effect.target,
            operation=effect.operation,
            command_id=command.id,
            command_key=command.command_key,
            command_type=command.command_type,
            command_payload=dict(command.payload),
            task_id=task.id,
            source_system=task.source_system,
            source_id=task.source_id,
            title=task.title,
            category=task.category,
            duration_minutes=task.duration_minutes,
            timezone=task.timezone,
            bindings=bindings,
            prior_results=prior,
        )

    def _complete_effect(
        self, effect_id: str, worker_id: str, result: dict[str, Any]
    ) -> None:
        effect = self.session.get(CommandEffect, effect_id)
        if effect is None:
            raise PermanentEffectError(f"Effect {effect_id} disappeared")
        if effect.status == CommandEffectStatus.COMPLETED.value:
            return
        if effect.status != CommandEffectStatus.RUNNING.value or effect.lease_owner != worker_id:
            raise RetryableEffectError("Effect lease was lost before completion checkpoint")
        now = datetime.now(UTC)
        effect.status = CommandEffectStatus.COMPLETED.value
        effect.result_payload = result
        effect.last_error = None
        effect.lease_owner = None
        effect.lease_until = None
        effect.next_attempt_at = None
        effect.updated_at = now
        effect.completed_at = now
        self.session.commit()

    def _retry_effect(self, effect_id: str, worker_id: str, error: str) -> bool:
        effect = self.session.get(CommandEffect, effect_id)
        if effect is None:
            return False
        if effect.status != CommandEffectStatus.RUNNING.value or effect.lease_owner != worker_id:
            return True
        now = datetime.now(UTC)
        if effect.attempt_count >= self.settings.worker_max_attempts:
            effect.status = CommandEffectStatus.FAILED.value
            effect.last_error = error[:4000]
            effect.lease_owner = None
            effect.lease_until = None
            effect.updated_at = now
            effect.completed_at = now
            self.session.commit()
            return False
        delay = min(
            self.settings.worker_retry_base_seconds * (2 ** max(0, effect.attempt_count - 1)),
            self.settings.worker_retry_max_seconds,
        )
        effect.status = CommandEffectStatus.RETRYABLE.value
        effect.last_error = error[:4000]
        effect.next_attempt_at = now + timedelta(seconds=delay)
        effect.lease_owner = None
        effect.lease_until = None
        effect.updated_at = now
        self.session.commit()
        return True

    def _terminal_effect_failure(self, effect_id: str, worker_id: str, error: str) -> None:
        effect = self.session.get(CommandEffect, effect_id)
        if effect is None:
            return
        if effect.status == CommandEffectStatus.COMPLETED.value:
            raise PermanentEffectError("Cannot convert a completed effect into a failure")
        if effect.status == CommandEffectStatus.RUNNING.value and effect.lease_owner != worker_id:
            raise RetryableEffectError("Effect lease was lost before terminal failure checkpoint")
        now = datetime.now(UTC)
        effect.status = CommandEffectStatus.FAILED.value
        effect.last_error = error[:4000]
        effect.lease_owner = None
        effect.lease_until = None
        effect.updated_at = now
        effect.completed_at = now
        self.session.commit()

    def _fail_command(self, command: OrchestrationCommand, error: str) -> None:
        self.session.refresh(command)
        if command.status != OrchestrationCommandStatus.ACCEPTED.value:
            return
        CommandService(self.session).complete(
            command.id,
            OrchestrationCommandComplete(
                success=False,
                result={"effects": self._effect_results(command.id)},
                error=error[:4000],
            ),
        )

    def _effect_results(self, command_id: str) -> dict[str, Any]:
        return {
            f"{effect.target}.{effect.operation}": {
                "status": effect.status,
                "result": effect.result_payload or {},
                "error": effect.last_error,
            }
            for effect in self.effects_for_command(command_id)
        }

    def _apply_local_projection(
        self, command_id: str, operation: str, adapter_result: dict[str, Any]
    ) -> None:
        command = self.session.get(OrchestrationCommand, command_id)
        if command is None:
            return
        task = self.session.get(Task, command.task_id)
        if task is None:
            return
        now = datetime.now(UTC)
        if operation == "ensure_execution" and adapter_result.get("event_id"):
            calendar_id = str(adapter_result["calendar_id"])
            event_id = str(adapter_result["event_id"])
            start = datetime.fromisoformat(str(adapter_result["start"]).replace("Z", "+00:00"))
            end = datetime.fromisoformat(str(adapter_result["end"]).replace("Z", "+00:00"))
            for binding in task.calendar_bindings:
                if binding.event_id != event_id and binding.followup_status == FollowupStatus.PENDING.value:
                    binding.followup_status = FollowupStatus.CANCELLED.value
                    binding.followup_handled_at = now
                    binding.updated_at = now
            binding = self.session.scalar(
                select(CalendarBinding).where(
                    CalendarBinding.provider == "google_calendar",
                    CalendarBinding.calendar_id == calendar_id,
                    CalendarBinding.event_id == event_id,
                )
            )
            if binding is None:
                binding = CalendarBinding(
                    task_id=task.id,
                    provider="google_calendar",
                    calendar_id=calendar_id,
                    event_id=event_id,
                    scheduled_start=start,
                    scheduled_end=end,
                    followup_due_at=end
                    + timedelta(minutes=self.settings.followup_delay_minutes),
                )
                self.session.add(binding)
            else:
                if binding.task_id != task.id:
                    raise PermanentEffectError("Calendar event is bound to a different Task Engine task")
                binding.scheduled_start = start
                binding.scheduled_end = end
                binding.followup_due_at = end + timedelta(
                    minutes=self.settings.followup_delay_minutes
                )
                binding.followup_status = FollowupStatus.PENDING.value
                binding.followup_handled_at = None
                binding.updated_at = now
        elif operation == "complete":
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = now
            self._close_pending_bindings(task, now)
        elif operation == "wait":
            task.status = TaskStatus.WAITING.value
            self._close_pending_bindings(task, now)
        elif operation == "cancel":
            task.status = TaskStatus.CANCELLED.value
            self._close_pending_bindings(task, now)
        elif operation == "defer":
            task.status = TaskStatus.OPEN.value
            self._close_pending_bindings(task, now)
        elif operation == "reschedule":
            task.status = TaskStatus.SCHEDULED.value
        if operation in {"complete", "wait", "cancel", "defer", "reschedule"}:
            task.version += 1
            task.updated_at = now
        self.session.commit()

    @staticmethod
    def _close_pending_bindings(task: Task, now: datetime) -> None:
        for binding in task.calendar_bindings:
            if binding.followup_status == FollowupStatus.PENDING.value:
                binding.followup_status = FollowupStatus.HANDLED.value
                binding.followup_handled_at = now
                binding.updated_at = now
