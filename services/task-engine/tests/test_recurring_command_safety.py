from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from task_engine.config import Settings
from task_engine.models import CalendarBinding, Task
from task_engine.worker.adapters import EffectEnvelope
from task_engine.worker.runtime import ProductionCommandWorker


class CanonicalRecurringAdapter:
    def __init__(self) -> None:
        self.calls: list[EffectEnvelope] = []

    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]:
        self.calls.append(envelope)
        return {
            "mode": "recurring_occurrence",
            "state": envelope.operation,
            "occurrence_key": "occurrence-1",
        }


class CalendarPresentationAdapter:
    def __init__(self) -> None:
        self.calls: list[EffectEnvelope] = []

    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]:
        self.calls.append(envelope)
        return {"applied": True, "event_id": "occurrence-event-1"}


def task_payload() -> dict[str, object]:
    return {
        "source_system": "neon_llm4life",
        "source_id": "66666666-6666-6666-6666-666666666666",
        "title": "Recurring routine",
        "category": "health_routine",
        "execution_policy": "movable",
        "priority": 50,
        "consequence_of_delay": 40,
        "duration_minutes": 30,
        "timezone": "America/Toronto",
    }


def recurring_metadata(event_id: str) -> dict[str, object]:
    start = datetime.now(UTC) - timedelta(hours=1)
    return {
        "canonical_action_id": "66666666-6666-6666-6666-666666666666",
        "template_id": "77777777-7777-7777-7777-777777777777",
        "occurrence_key": "occurrence-1",
        "occurrence_start": start.isoformat(),
        "occurrence_end": (start + timedelta(minutes=30)).isoformat(),
        "calendar_event_id": event_id,
    }


def test_recurring_completion_does_not_terminally_complete_task_engine_template(
    client: TestClient,
    session: Session,
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload()).json()
    start = datetime.now(UTC) - timedelta(hours=1)
    first = client.post(
        f"/v1/tasks/{task['id']}/calendar-bindings",
        json={
            "calendar_id": "routine@example.test",
            "event_id": "occurrence-event-1",
            "scheduled_start": start.isoformat(),
            "scheduled_end": (start + timedelta(minutes=30)).isoformat(),
        },
    ).json()
    future = datetime.now(UTC) + timedelta(days=1)
    second = client.post(
        f"/v1/tasks/{task['id']}/calendar-bindings",
        json={
            "calendar_id": "routine@example.test",
            "event_id": "occurrence-event-2",
            "scheduled_start": future.isoformat(),
            "scheduled_end": (future + timedelta(minutes=30)).isoformat(),
        },
    ).json()
    task = client.get(f"/v1/tasks/{task['id']}").json()
    command = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json={
            "command_key": "recurring:complete:1",
            "command_type": "complete",
            "expected_task_version": task["version"],
            "metadata": recurring_metadata("occurrence-event-1"),
        },
    )
    assert command.status_code == 202

    canonical = CanonicalRecurringAdapter()
    calendar = CalendarPresentationAdapter()
    worker = ProductionCommandWorker(
        session,
        Settings(),
        {"canonical": canonical, "calendar": calendar},
    )
    result = worker.run(worker_id="recurring-worker")

    assert result.commands_completed == 1
    stored_task = session.get(Task, task["id"])
    assert stored_task is not None
    assert stored_task.status == "scheduled"
    assert stored_task.completed_at is None
    first_binding = session.get(CalendarBinding, first["id"])
    second_binding = session.get(CalendarBinding, second["id"])
    assert first_binding is not None and first_binding.followup_status == "handled"
    assert second_binding is not None and second_binding.followup_status == "pending"


def test_recurring_generic_reschedule_is_rejected_before_worker_side_effects(
    client: TestClient,
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload()).json()
    start = datetime.now(UTC) + timedelta(hours=2)
    response = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json={
            "command_key": "recurring:unsafe-reschedule:1",
            "command_type": "reschedule",
            "expected_task_version": task["version"],
            "desired_start": start.isoformat(),
            "desired_end": (start + timedelta(minutes=30)).isoformat(),
            "metadata": recurring_metadata("occurrence-event-1"),
        },
    )

    assert response.status_code == 409
    assert "occurrence-specific planning/recovery protocol" in response.json()["detail"]
