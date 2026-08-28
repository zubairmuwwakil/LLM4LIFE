from fastapi.testclient import TestClient


def test_outbox_is_durable_and_acknowledgeable(client: TestClient) -> None:
    task = client.post(
        "/v1/tasks/sync",
        json={
            "source_system": "jira",
            "source_id": "ENG-42",
            "title": "Fix integration bug",
            "category": "work_learning",
        },
    )
    assert task.status_code == 200

    pending = client.get("/v1/outbox")
    assert pending.status_code == 200
    assert len(pending.json()) == 1
    event = pending.json()[0]
    assert event["event_type"] == "task.synced"

    ack = client.post(f"/v1/outbox/{event['id']}/ack")
    assert ack.status_code == 200
    assert ack.json()["status"] == "published"
    assert client.get("/v1/outbox").json() == []
