from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def task_payload(source_id: str = "things-123") -> dict[str, object]:
    return {
        "source_system": "things3",
        "source_id": source_id,
        "title": "Call insurer",
        "category": "admin_money",
        "execution_policy": "movable",
        "priority": 60,
        "consequence_of_delay": 65,
        "duration_minutes": 30,
        "timezone": "America/Toronto",
    }


def test_sync_is_idempotent(client: TestClient) -> None:
    first = client.post("/v1/tasks/sync", json=task_payload())
    second = client.post("/v1/tasks/sync", json=task_payload())

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["version"] == first.json()["version"]


def test_followup_is_explicit_and_only_fires_when_due(client: TestClient) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload()).json()
    start = datetime.now(UTC) - timedelta(hours=2)
    end = start + timedelta(minutes=30)
    binding = client.post(
        f"/v1/tasks/{task['id']}/calendar-bindings",
        json={
            "provider": "google_calendar",
            "calendar_id": "primary",
            "event_id": "event-123",
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
        },
    )
    assert binding.status_code == 201

    due = client.get("/v1/followups/due", params={"now": datetime.now(UTC).isoformat()})
    assert due.status_code == 200
    assert len(due.json()) == 1
    assert due.json()[0]["task"]["id"] == task["id"]

    resolved = client.post(
        f"/v1/followups/{binding.json()['id']}/resolve",
        json={"result": "completed"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["task"]["status"] == "completed"

    due_again = client.get("/v1/followups/due", params={"now": datetime.now(UTC).isoformat()})
    assert due_again.json() == []


def test_duplicate_calendar_binding_does_not_duplicate_followup(client: TestClient) -> None:
    task = client.post("/v1/tasks/sync", json=task_payload()).json()
    start = datetime.now(UTC) + timedelta(hours=1)
    payload = {
        "provider": "google_calendar",
        "calendar_id": "primary",
        "event_id": "event-dedup",
        "scheduled_start": start.isoformat(),
        "scheduled_end": (start + timedelta(minutes=30)).isoformat(),
    }

    first = client.post(f"/v1/tasks/{task['id']}/calendar-bindings", json=payload)
    second = client.post(f"/v1/tasks/{task['id']}/calendar-bindings", json=payload)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
