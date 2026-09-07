from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from task_engine.models import OutboxEvent


def task_payload(source_id: str = "command-task", execution_policy: str = "movable") -> dict[str, object]:
    return {
        "source_system": "neon_llm4life",
        "source_id": source_id,
        "title": "File taxes",
        "category": "admin_money",
        "execution_policy": execution_policy,
        "priority": 80,
        "consequence_of_delay": 90,
        "duration_minutes": 60,
        "timezone": "America/Toronto",
    }


def reschedule_payload(command_key: str, version: int) -> dict[str, object]:
    start = datetime.now(UTC) + timedelta(hours=3)
    return {
        "command_key": command_key,
        "command_type": "reschedule",
        "expected_task_version": version,
        "requested_by": "chatgpt",
        "reason": "Still valuable; move to the next realistic open block.",
        "desired_start": start.isoformat(),
        "desired_end": (start + timedelta(hours=1)).isoformat(),
        "metadata": {"source": "daily_planner"},
    }


def test_command_submission_is_idempotent_and_emits_one_request(
    client: TestClient,
    session: Session,
) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload()).json()
    payload = reschedule_payload("daily:taxes:miss-1", task["version"])

    first = client.post(f"/v1/tasks/{task['id']}/commands", json=payload)
    second = client.post(f"/v1/tasks/{task['id']}/commands", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == "accepted"

    events = list(
        session.scalars(
            select(OutboxEvent).where(
                OutboxEvent.idempotency_key == "command:daily:taxes:miss-1:requested"
            )
        )
    )
    assert len(events) == 1
    assert events[0].event_type == "orchestration.reschedule.requested"


def test_same_command_key_cannot_be_reused_for_different_decision(client: TestClient) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("command-conflict")).json()
    payload = reschedule_payload("daily:conflict:1", task["version"])
    first = client.post(f"/v1/tasks/{task['id']}/commands", json=payload)
    assert first.status_code == 202

    changed = dict(payload)
    changed["reason"] = "Different decision under the same idempotency key."
    second = client.post(f"/v1/tasks/{task['id']}/commands", json=changed)

    assert second.status_code == 409


def test_stale_task_version_is_rejected(client: TestClient) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("command-version")).json()
    updated = client.patch(
        f"/v1/tasks/{task['id']}",
        json={"priority": 95, "expected_version": task["version"]},
    )
    assert updated.status_code == 200

    command = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json=reschedule_payload("daily:stale:1", task["version"]),
    )
    assert command.status_code == 409
    assert "Version mismatch" in command.json()["detail"]


def test_fixed_task_cannot_receive_reschedule_command(client: TestClient) -> None:
    task = client.post(
        "/v1/tasks/sync",
        json=task_payload("command-fixed", execution_policy="fixed"),
    ).json()

    command = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json=reschedule_payload("daily:fixed:1", task["version"]),
    )

    assert command.status_code == 409
    assert "Fixed tasks cannot be rescheduled" in command.json()["detail"]


def test_command_completion_is_idempotent_but_conflicts_are_rejected(client: TestClient) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("command-complete")).json()
    command = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json={
            "command_key": "daily:complete:1",
            "command_type": "complete",
            "expected_task_version": task["version"],
            "requested_by": "chatgpt",
            "reason": "User explicitly reported completion.",
            "metadata": {"source": "chat"},
        },
    ).json()

    completed = client.post(
        f"/v1/commands/{command['id']}/complete",
        json={"success": True, "result": {"calendar_updated": True, "canonical_updated": True}},
    )
    replay = client.post(
        f"/v1/commands/{command['id']}/complete",
        json={"success": True, "result": {"calendar_updated": True, "canonical_updated": True}},
    )
    conflicting = client.post(
        f"/v1/commands/{command['id']}/complete",
        json={"success": False, "result": {}, "error": "late conflicting failure"},
    )

    assert completed.status_code == 200
    assert replay.status_code == 200
    assert completed.json()["status"] == "completed"
    assert replay.json()["id"] == completed.json()["id"]
    assert conflicting.status_code == 409


def test_reschedule_requires_a_complete_window(client: TestClient) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload("command-window")).json()

    response = client.post(
        f"/v1/tasks/{task['id']}/commands",
        json={
            "command_key": "daily:window:1",
            "command_type": "reschedule",
            "expected_task_version": task["version"],
            "desired_start": datetime.now(UTC).isoformat(),
        },
    )

    assert response.status_code == 422
