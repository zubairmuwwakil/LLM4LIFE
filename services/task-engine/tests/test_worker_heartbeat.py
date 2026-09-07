from sqlalchemy.orm import Session

from task_engine.config import Settings
from task_engine.models import WorkerHeartbeat
from task_engine.services.worker_service import CommandWorker


def test_empty_worker_run_records_successful_heartbeat(session: Session) -> None:
    worker = CommandWorker(session, Settings(), {})

    result = worker.run(worker_id="heartbeat-test", max_commands=5)

    assert result.commands_seen == 0
    heartbeat = session.get(WorkerHeartbeat, "command_worker")
    assert heartbeat is not None
    assert heartbeat.worker_id == "heartbeat-test"
    assert heartbeat.last_started_at is not None
    assert heartbeat.last_succeeded_at is not None
    assert heartbeat.last_failed_at is None
    assert heartbeat.last_commands_seen == 0
    assert heartbeat.last_commands_completed == 0
    assert heartbeat.last_error_class is None
