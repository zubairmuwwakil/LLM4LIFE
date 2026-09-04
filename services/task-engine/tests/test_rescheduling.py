from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient


TZ = ZoneInfo("America/Toronto")


def create_task(client: TestClient, priority: int = 50, consequence: int = 50) -> dict[str, object]:
    response = client.post(
        "/v1/tasks/sync",
        json={
            "source_system": "things3",
            "source_id": f"task-{priority}-{consequence}",
            "title": "Movable admin task",
            "category": "admin_money",
            "execution_policy": "movable",
            "priority": priority,
            "consequence_of_delay": consequence,
            "duration_minutes": 30,
            "timezone": "America/Toronto",
        },
    )
    assert response.status_code == 200
    return response.json()


def miss_once(client: TestClient, task_id: str, event_id: str, day: int) -> None:
    start = datetime(2026, 8, day, 14, 0, tzinfo=TZ)
    binding = client.post(
        f"/v1/tasks/{task_id}/calendar-bindings",
        json={
            "provider": "google_calendar",
            "calendar_id": "primary",
            "event_id": event_id,
            "scheduled_start": start.isoformat(),
            "scheduled_end": start.replace(minute=30).isoformat(),
        },
    ).json()
    response = client.post(
        f"/v1/followups/{binding['id']}/resolve",
        json={"result": "missed"},
    )
    assert response.status_code == 200


def test_planner_prefers_near_realistic_window(client: TestClient) -> None:
    task = create_task(client, priority=70, consequence=80)
    response = client.post(
        f"/v1/tasks/{task['id']}/plan",
        json={
            "now": "2026-08-28T12:00:00-04:00",
            "candidate_windows": [
                {"start": "2026-08-30T15:00:00-04:00", "end": "2026-08-30T15:30:00-04:00"},
                {"start": "2026-08-28T14:00:00-04:00", "end": "2026-08-28T14:30:00-04:00"},
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["recommended"]["start"].startswith("2026-08-28T14:00:00")


def test_planner_rejects_outside_movable_window(client: TestClient) -> None:
    task = create_task(client, priority=70, consequence=80)
    response = client.post(
        f"/v1/tasks/{task['id']}/plan",
        json={
            "now": "2026-08-28T12:00:00-04:00",
            "candidate_windows": [
                {"start": "2026-08-29T10:00:00-04:00", "end": "2026-08-29T10:30:00-04:00"}
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["recommended"] is None
    assert response.json()["requires_review"] is True


def test_repeated_low_stakes_misses_stop_blind_rescheduling(client: TestClient) -> None:
    task = create_task(client, priority=40, consequence=30)
    for index, day in enumerate((25, 26, 27), start=1):
        miss_once(client, str(task["id"]), f"miss-{index}", day)

    response = client.post(
        f"/v1/tasks/{task['id']}/plan",
        json={
            "now": "2026-08-28T12:00:00-04:00",
            "candidate_windows": [
                {"start": "2026-08-28T16:00:00-04:00", "end": "2026-08-28T16:30:00-04:00"}
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["recommended"] is None
    assert response.json()["requires_review"] is True
    assert "Repeated misses" in response.json()["reason"]


def test_high_stakes_task_can_still_be_rescheduled_after_misses(client: TestClient) -> None:
    task = create_task(client, priority=90, consequence=90)
    for index, day in enumerate((25, 26, 27), start=1):
        miss_once(client, str(task["id"]), f"high-{index}", day)

    response = client.post(
        f"/v1/tasks/{task['id']}/plan",
        json={
            "now": "2026-08-28T12:00:00-04:00",
            "candidate_windows": [
                {"start": "2026-08-28T16:00:00-04:00", "end": "2026-08-28T16:30:00-04:00"}
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["recommended"] is not None
