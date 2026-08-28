from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from task_engine.auth import require_api_token
from task_engine.config import get_settings
from task_engine.database import get_session
from task_engine.schemas import (
    CalendarBindingCreate,
    CalendarBindingRead,
    FollowupDue,
    FollowupResolution,
    FollowupResolve,
    OutboxEventRead,
    PlanningRecommendation,
    PlanningRequest,
    TaskCreate,
    TaskRead,
    TaskSync,
    TaskUpdate,
)
from task_engine.services.planner import Planner
from task_engine.services.task_service import ConflictError, NotFoundError, TaskService

router = APIRouter(prefix="/v1", dependencies=[Depends(require_api_token)])


def service(session: Session = Depends(get_session)) -> TaskService:
    return TaskService(session, get_settings())


def translate_error(exc: Exception) -> HTTPException:
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, ConflictError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unexpected error")


@router.post("/tasks", response_model=TaskRead, status_code=status.HTTP_201_CREATED)
def create_task(data: TaskCreate, svc: TaskService = Depends(service)) -> TaskRead:
    try:
        return TaskRead.model_validate(svc.create_task(data))
    except (NotFoundError, ConflictError) as exc:
        raise translate_error(exc) from exc


@router.post("/tasks/sync", response_model=TaskRead)
def sync_task(data: TaskSync, svc: TaskService = Depends(service)) -> TaskRead:
    try:
        return TaskRead.model_validate(svc.sync_task(data))
    except (NotFoundError, ConflictError) as exc:
        raise translate_error(exc) from exc


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(
    task_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    svc: TaskService = Depends(service),
) -> list[TaskRead]:
    return [TaskRead.model_validate(task) for task in svc.list_tasks(task_status, limit)]


@router.get("/tasks/{task_id}", response_model=TaskRead)
def get_task(task_id: str, svc: TaskService = Depends(service)) -> TaskRead:
    try:
        return TaskRead.model_validate(svc.get_task(task_id))
    except NotFoundError as exc:
        raise translate_error(exc) from exc


@router.patch("/tasks/{task_id}", response_model=TaskRead)
def update_task(task_id: str, data: TaskUpdate, svc: TaskService = Depends(service)) -> TaskRead:
    try:
        return TaskRead.model_validate(svc.update_task(task_id, data))
    except (NotFoundError, ConflictError) as exc:
        raise translate_error(exc) from exc


@router.post(
    "/tasks/{task_id}/calendar-bindings",
    response_model=CalendarBindingRead,
    status_code=status.HTTP_201_CREATED,
)
def bind_calendar(
    task_id: str,
    data: CalendarBindingCreate,
    svc: TaskService = Depends(service),
) -> CalendarBindingRead:
    try:
        return CalendarBindingRead.model_validate(svc.bind_calendar(task_id, data))
    except (NotFoundError, ConflictError) as exc:
        raise translate_error(exc) from exc


@router.get("/followups/due", response_model=list[FollowupDue])
def due_followups(
    now: datetime | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    svc: TaskService = Depends(service),
) -> list[FollowupDue]:
    due = svc.due_followups(now=now, limit=limit)
    return [
        FollowupDue(
            binding=CalendarBindingRead.model_validate(binding),
            task=TaskRead.model_validate(svc.get_task(binding.task_id)),
        )
        for binding in due
    ]


@router.post("/followups/{binding_id}/resolve", response_model=FollowupResolution)
def resolve_followup(
    binding_id: str,
    data: FollowupResolve,
    svc: TaskService = Depends(service),
) -> FollowupResolution:
    try:
        task, attempt, binding = svc.resolve_followup(binding_id, data)
    except (NotFoundError, ConflictError) as exc:
        raise translate_error(exc) from exc
    return FollowupResolution(
        task=TaskRead.model_validate(task),
        attempt=attempt,
        binding=CalendarBindingRead.model_validate(binding),
    )


@router.post("/tasks/{task_id}/plan", response_model=PlanningRecommendation)
def plan_task(
    task_id: str,
    data: PlanningRequest,
    svc: TaskService = Depends(service),
) -> PlanningRecommendation:
    try:
        task = svc.get_task(task_id)
    except NotFoundError as exc:
        raise translate_error(exc) from exc
    return Planner(get_settings()).recommend(task, data.candidate_windows, data.now)


@router.get("/outbox", response_model=list[OutboxEventRead])
def pending_outbox(
    limit: int = Query(default=100, ge=1, le=500),
    svc: TaskService = Depends(service),
) -> list[OutboxEventRead]:
    return [OutboxEventRead.model_validate(event) for event in svc.pending_outbox(limit)]


@router.post("/outbox/{event_id}/ack", response_model=OutboxEventRead)
def ack_outbox(event_id: str, svc: TaskService = Depends(service)) -> OutboxEventRead:
    try:
        return OutboxEventRead.model_validate(svc.ack_outbox(event_id))
    except NotFoundError as exc:
        raise translate_error(exc) from exc
