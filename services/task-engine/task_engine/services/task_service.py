from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from task_engine.config import Settings
from task_engine.enums import AttemptResult, FollowupStatus, OutboxStatus, TaskStatus
from task_engine.models import CalendarBinding, OutboxEvent, Task, TaskAttempt
from task_engine.schemas import CalendarBindingCreate, FollowupResolve, TaskCreate, TaskSync, TaskUpdate


class NotFoundError(LookupError):
    pass


class ConflictError(RuntimeError):
    pass


class TaskService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    def create_task(self, data: TaskCreate) -> Task:
        source_id = data.source_id or str(uuid.uuid4())
        task = Task(source_system=data.source_system, source_id=source_id)
        self._apply_task_fields(task, data)
        self.session.add(task)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("A task with this source identity already exists") from exc
        self._emit(task, "task.created", suffix="created")
        self.session.commit()
        self.session.refresh(task)
        return task

    def sync_task(self, data: TaskSync) -> Task:
        stmt = select(Task).where(
            Task.source_system == data.source_system,
            Task.source_id == data.source_id,
        )
        task = self.session.scalar(stmt)
        if task is None:
            task = Task(source_system=data.source_system, source_id=data.source_id)
            self._apply_task_fields(task, data)
            self.session.add(task)
            self.session.flush()
            self._emit(task, "task.synced", suffix=f"sync-v{task.version}")
        else:
            changed = self._apply_task_fields(task, data)
            if changed:
                self._touch(task)
                self._emit(task, "task.synced", suffix=f"sync-v{task.version}")
        self.session.commit()
        self.session.refresh(task)
        return task

    def get_task(self, task_id: str) -> Task:
        task = self.session.get(Task, task_id)
        if task is None:
            raise NotFoundError(f"Task {task_id} not found")
        return task

    def list_tasks(self, status: str | None = None, limit: int = 100) -> list[Task]:
        stmt = select(Task).order_by(Task.updated_at.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(Task.status == status)
        return list(self.session.scalars(stmt))

    def update_task(self, task_id: str, data: TaskUpdate) -> Task:
        task = self.get_task(task_id)
        if data.expected_version is not None and data.expected_version != task.version:
            raise ConflictError(
                f"Version mismatch: expected {data.expected_version}, current {task.version}"
            )

        payload = data.model_dump(exclude_unset=True, exclude={"expected_version"})
        for key, value in payload.items():
            if hasattr(value, "value"):
                value = value.value
            setattr(task, key, value)
        self._touch(task)
        self._emit(task, "task.updated", suffix=f"updated-v{task.version}")
        self.session.commit()
        self.session.refresh(task)
        return task

    def bind_calendar(self, task_id: str, data: CalendarBindingCreate) -> CalendarBinding:
        task = self.get_task(task_id)
        if task.status in {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value}:
            raise ConflictError("Completed or cancelled tasks cannot receive new Calendar bindings")
        existing = self.session.scalar(
            select(CalendarBinding).where(
                CalendarBinding.provider == data.provider,
                CalendarBinding.calendar_id == data.calendar_id,
                CalendarBinding.event_id == data.event_id,
            )
        )
        if existing is not None:
            if existing.task_id != task.id:
                raise ConflictError("Calendar event is already bound to another task")
            return existing

        followup_due_at = data.scheduled_end + timedelta(minutes=self.settings.followup_delay_minutes)
        binding = CalendarBinding(
            task_id=task.id,
            provider=data.provider,
            calendar_id=data.calendar_id,
            event_id=data.event_id,
            scheduled_start=data.scheduled_start,
            scheduled_end=data.scheduled_end,
            followup_due_at=followup_due_at,
        )
        self.session.add(binding)
        if task.status not in {TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value}:
            task.status = TaskStatus.SCHEDULED.value
            self._touch(task)
        self.session.flush()
        self._emit(
            task,
            "calendar.binding.created",
            suffix=f"binding-{binding.id}",
            payload={"binding_id": binding.id, "event_id": data.event_id},
        )
        self.session.commit()
        self.session.refresh(binding)
        return binding

    def due_followups(self, now: datetime | None = None, limit: int = 100) -> list[CalendarBinding]:
        now = now or datetime.now(UTC)
        stmt = (
            select(CalendarBinding)
            .join(Task, Task.id == CalendarBinding.task_id)
            .where(
                CalendarBinding.followup_status == FollowupStatus.PENDING.value,
                CalendarBinding.followup_due_at <= now,
                Task.status.notin_([TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]),
            )
            .order_by(CalendarBinding.followup_due_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def resolve_followup(
        self,
        binding_id: str,
        data: FollowupResolve,
    ) -> tuple[Task, TaskAttempt, CalendarBinding]:
        binding = self.session.get(CalendarBinding, binding_id)
        if binding is None:
            raise NotFoundError(f"Calendar binding {binding_id} not found")
        if binding.followup_status != FollowupStatus.PENDING.value:
            raise ConflictError("Follow-up has already been handled")

        task = self.get_task(binding.task_id)
        task.attempt_count += 1
        if data.result in {AttemptResult.MISSED, AttemptResult.SKIPPED}:
            task.miss_count += 1

        attempt = TaskAttempt(
            task_id=task.id,
            ordinal=task.attempt_count,
            result=data.result.value,
            scheduled_start=binding.scheduled_start,
            scheduled_end=binding.scheduled_end,
            note=data.note,
        )
        self.session.add(attempt)

        if data.result == AttemptResult.COMPLETED:
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.now(UTC)
            event_type = "task.completed"
        else:
            high_stakes = (
                max(task.priority, task.consequence_of_delay) >= self.settings.high_stakes_threshold
            )
            if task.miss_count >= self.settings.misses_before_review and not high_stakes:
                task.status = TaskStatus.NEEDS_REVIEW.value
                event_type = "task.needs_review"
            else:
                task.status = TaskStatus.NEEDS_RESCHEDULE.value
                event_type = "task.needs_reschedule"

        binding.followup_status = FollowupStatus.HANDLED.value
        binding.followup_handled_at = datetime.now(UTC)
        binding.updated_at = datetime.now(UTC)
        self._touch(task)
        self.session.flush()
        self._emit(
            task,
            event_type,
            suffix=f"attempt-{attempt.ordinal}",
            payload={
                "attempt_id": attempt.id,
                "binding_id": binding.id,
                "result": data.result.value,
                "miss_count": task.miss_count,
            },
        )
        self.session.commit()
        self.session.refresh(task)
        self.session.refresh(attempt)
        self.session.refresh(binding)
        return task, attempt, binding

    def pending_outbox(self, limit: int = 100) -> list[OutboxEvent]:
        stmt = (
            select(OutboxEvent)
            .where(OutboxEvent.status == OutboxStatus.PENDING.value)
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def ack_outbox(self, event_id: str) -> OutboxEvent:
        event = self.session.get(OutboxEvent, event_id)
        if event is None:
            raise NotFoundError(f"Outbox event {event_id} not found")
        event.status = OutboxStatus.PUBLISHED.value
        event.published_at = datetime.now(UTC)
        self.session.commit()
        self.session.refresh(event)
        return event

    def _apply_task_fields(self, task: Task, data: TaskCreate | TaskSync) -> bool:
        changed = False
        payload = data.model_dump(exclude={"source_system", "source_id"})
        for key, value in payload.items():
            if hasattr(value, "value"):
                value = value.value
            if getattr(task, key, None) != value:
                setattr(task, key, value)
                changed = True
        return changed

    @staticmethod
    def _touch(task: Task) -> None:
        task.version += 1
        task.updated_at = datetime.now(UTC)

    def _emit(
        self,
        task: Task,
        event_type: str,
        suffix: str,
        payload: dict[str, object] | None = None,
    ) -> None:
        event = OutboxEvent(
            event_type=event_type,
            aggregate_id=task.id,
            idempotency_key=f"{task.id}:{suffix}",
            payload={
                "task_id": task.id,
                "source_system": task.source_system,
                "source_id": task.source_id,
                "status": task.status,
                **(payload or {}),
            },
        )
        self.session.add(event)
