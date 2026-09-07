from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from task_engine.config import Settings
from task_engine.enums import CommandEffectStatus
from task_engine.models import CalendarBinding, CommandEffect, OrchestrationCommand, Task
from task_engine.services.worker_service import CommandWorker
from task_engine.worker.adapters import EffectEnvelope, PermanentEffectError, RetryableEffectError


class RecordingAdapter:
    def __init__(self, results: dict[str, dict[str, Any]] | None = None) -> None:
        self.results = results or {}
        self.calls: list[EffectEnvelope] = []

    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]:
        self.calls.append(envelope)
        return dict(self.results.get(envelope.operation, {"applied": True, "operation": envelope.operation}))


class FailOnceAdapter(RecordingAdapter):
    def __init__(self, operation: str) -> None:
        super().__init__()
        self.operation = operation
        self.failed = False

    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]:
        self.calls.append(envelope)
        if envelope.operation == self.operation and not self.failed:
            self.failed = True
            raise RetryableEffectError("temporary provider failure")
        return {"applied": True, "operation": envelope.operation}


class PermanentFailureAdapter(RecordingAdapter):
    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]:
        self.calls.append(envelope)
        raise PermanentEffectError("invalid external contract")


def task_payload(source_id: str) -> dict[str, object]:
    return {
        "source_system": "neon_llm4life",
        "source_id": source_id,
        "title": "Production command test",
        "category": "admin_money",
        "execution_policy": "movable",
        "priority": 70,
        "consequence_of_delay": 70,
        "duration_minutes": 30,
        "timezone": "America/Toronto",
    }


def settings() -> Settings:
    return Settings(
        worker_lease_seconds=60,
        worker_max_attempts=3,
        worker_retry_base_seconds=1,
        worker_retry_max_seconds=30,
    )


def submit_complete(client: TestClient, task: dict[str, Any], key: str) -> dict[str, Any]:
    response = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json={
            "command_key": key,
            "command_type": "complete",
            "expected_task_version": task["version"],
            "reason": "User explicitly reported completion.",
            "metadata": {"source": "test"},
        },
    )
    assert response.status_code == 202
    return response.json()


def test_complete_runs_ordered_effects_once_and_finalizes_command(
    client: TestClient, session: Session
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("11111111-1111-1111-1111-111111111111")).json()
    command = submit_complete(client, task, "worker:complete:1")
    canonical = RecordingAdapter()
    calendar = RecordingAdapter()
    worker = CommandWorker(session, settings(), {"canonical": canonical, "calendar": calendar})

    first = worker.run(worker_id="worker-a")
    second = worker.run(worker_id="worker-a")

    assert first.commands_completed == 1
    assert first.effects_applied == 2
    assert second.commands_seen == 0
    assert [call.operation for call in canonical.calls] == ["complete"]
    assert [call.operation for call in calendar.calls] == ["mark_completed"]

    stored = session.get(OrchestrationCommand, command["id"])
    assert stored is not None and stored.status == "completed"
    stored_task = session.get(Task, task["id"])
    assert stored_task is not None and stored_task.status == "completed"
    effects = list(
        session.scalars(
            select(CommandEffect)
            .where(CommandEffect.command_id == command["id"])
            .order_by(CommandEffect.ordinal)
        )
    )
    assert [effect.status for effect in effects] == ["completed", "completed"]


def test_retry_resumes_from_failed_step_without_replaying_completed_step(
    client: TestClient, session: Session
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("22222222-2222-2222-2222-222222222222")).json()
    command = submit_complete(client, task, "worker:retry:1")
    canonical = RecordingAdapter()
    calendar = FailOnceAdapter("mark_completed")
    worker = CommandWorker(session, settings(), {"canonical": canonical, "calendar": calendar})

    first = worker.run(worker_id="worker-a")
    assert first.commands_completed == 0
    assert first.effects_applied == 1
    assert first.effects_retried == 1

    effects = worker.effects_for_command(command["id"])
    assert effects[0].status == CommandEffectStatus.COMPLETED.value
    assert effects[1].status == CommandEffectStatus.RETRYABLE.value
    effects[1].next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()

    second = worker.run(worker_id="worker-b")

    assert second.commands_completed == 1
    assert len(canonical.calls) == 1
    assert len(calendar.calls) == 2
    assert session.get(OrchestrationCommand, command["id"]).status == "completed"


def test_reschedule_passes_calendar_result_to_canonical_and_replaces_local_binding(
    client: TestClient, session: Session
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("33333333-3333-3333-3333-333333333333")).json()
    old_start = datetime.now(UTC) + timedelta(hours=1)
    old_binding = client.post(
        f"/v1/tasks/{task['id']}/calendar-bindings",
        json={
            "calendar_id": "personal@example.test",
            "event_id": "old-event",
            "scheduled_start": old_start.isoformat(),
            "scheduled_end": (old_start + timedelta(minutes=30)).isoformat(),
        },
    ).json()
    task = client.get(f"/v1/tasks/{task['id']}").json()
    new_start = datetime.now(UTC) + timedelta(hours=4)
    command_response = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json={
            "command_key": "worker:reschedule:1",
            "command_type": "reschedule",
            "expected_task_version": task["version"],
            "reason": "Move to the selected open block.",
            "desired_start": new_start.isoformat(),
            "desired_end": (new_start + timedelta(minutes=45)).isoformat(),
            "metadata": {"calendar_id": "personal@example.test"},
        },
    )
    assert command_response.status_code == 202
    command = command_response.json()

    calendar = RecordingAdapter(
        {
            "ensure_execution": {
                "applied": True,
                "calendar_id": "personal@example.test",
                "event_id": "new-event",
                "start": new_start.isoformat(),
                "end": (new_start + timedelta(minutes=45)).isoformat(),
            }
        }
    )
    canonical = RecordingAdapter()
    worker = CommandWorker(session, settings(), {"canonical": canonical, "calendar": calendar})

    result = worker.run(worker_id="worker-a")

    assert result.commands_completed == 1
    assert canonical.calls[0].operation == "reschedule"
    assert canonical.calls[0].prior_results["calendar.ensure_execution"]["event_id"] == "new-event"
    old = session.get(CalendarBinding, old_binding["id"])
    assert old is not None and old.followup_status == "cancelled"
    new = session.scalar(select(CalendarBinding).where(CalendarBinding.event_id == "new-event"))
    assert new is not None and new.followup_status == "pending"


def test_permanent_effect_failure_fails_command_without_running_later_effects(
    client: TestClient, session: Session
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("44444444-4444-4444-4444-444444444444")).json()
    command = submit_complete(client, task, "worker:permanent:1")
    canonical = PermanentFailureAdapter()
    calendar = RecordingAdapter()
    worker = CommandWorker(session, settings(), {"canonical": canonical, "calendar": calendar})

    result = worker.run(worker_id="worker-a")

    assert result.commands_failed == 1
    assert len(canonical.calls) == 1
    assert calendar.calls == []
    stored = session.get(OrchestrationCommand, command["id"])
    assert stored is not None and stored.status == "failed"
    effects = worker.effects_for_command(command["id"])
    assert effects[0].status == "failed"
    assert effects[1].status == "pending"


def test_expired_effect_lease_can_be_recovered_by_another_worker(
    client: TestClient, session: Session
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("55555555-5555-5555-5555-555555555555")).json()
    command = submit_complete(client, task, "worker:lease:1")
    canonical = RecordingAdapter()
    calendar = RecordingAdapter()
    worker = CommandWorker(session, settings(), {"canonical": canonical, "calendar": calendar})
    stored = session.get(OrchestrationCommand, command["id"])
    effects = worker.ensure_plan(stored)
    effects[0].status = "running"
    effects[0].lease_owner = "dead-worker"
    effects[0].lease_until = datetime.now(UTC) - timedelta(seconds=5)
    session.commit()

    result = worker.run(worker_id="replacement-worker")

    assert result.commands_completed == 1
    assert effects[0].attempt_count == 1
    assert len(canonical.calls) == 1
    assert len(calendar.calls) == 1
