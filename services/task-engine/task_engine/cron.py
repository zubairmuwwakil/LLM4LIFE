from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from task_engine.config import Settings, get_settings
from task_engine.database import get_session
from task_engine.schemas import WorkerRunResult
from task_engine.worker.calendar_adapter import GoogleCalendarAdapter
from task_engine.worker.canonical_adapter import CanonicalNeonAdapter
from task_engine.worker.runtime import ProductionCommandWorker

router = APIRouter()


def missing_runtime_configuration(settings: Settings) -> list[str]:
    missing: list[str] = []
    if not settings.database_url or settings.database_url.startswith("sqlite"):
        missing.append("TASK_ENGINE_DATABASE_URL")
    if not settings.canonical_database_url:
        missing.append("TASK_ENGINE_CANONICAL_DATABASE_URL")
    if not settings.google_client_id:
        missing.append("TASK_ENGINE_GOOGLE_CLIENT_ID")
    if not settings.google_client_secret:
        missing.append("TASK_ENGINE_GOOGLE_CLIENT_SECRET")
    if not settings.google_refresh_token:
        missing.append("TASK_ENGINE_GOOGLE_REFRESH_TOKEN")
    if not settings.cron_secret:
        missing.append("CRON_SECRET")
    return missing


def _authorize_cron(authorization: str | None, settings: Settings) -> None:
    if not settings.cron_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cron runtime is not configured",
        )
    expected = f"Bearer {settings.cron_secret}"
    if authorization is None or not secrets.compare_digest(authorization, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@router.get("/api/cron/worker", response_model=WorkerRunResult, include_in_schema=False)
def run_worker_cron(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
    session: Session = Depends(get_session),
) -> WorkerRunResult:
    _authorize_cron(authorization, settings)
    missing = missing_runtime_configuration(settings)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"runtime_not_ready": missing},
        )

    worker = ProductionCommandWorker(
        session,
        settings,
        {
            "canonical": CanonicalNeonAdapter(settings),
            "calendar": GoogleCalendarAdapter(settings),
        },
    )
    return worker.run(
        worker_id=f"vercel-cron:{uuid.uuid4()}",
        max_commands=settings.worker_batch_size,
    )
