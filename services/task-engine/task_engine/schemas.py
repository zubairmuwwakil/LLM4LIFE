from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from task_engine.enums import (
    AttemptResult,
    CommandEffectStatus,
    ExecutionPolicy,
    OrchestrationCommandStatus,
    OrchestrationCommandType,
    TaskCategory,
    TaskStatus,
)


class TaskBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    source_url: str | None = None
    source_revision: str | None = None
    notes_snapshot: str | None = None
    category: TaskCategory = TaskCategory.PERSONAL_LIFE
    execution_policy: ExecutionPolicy = ExecutionPolicy.MOVABLE
    priority: int = Field(default=50, ge=0, le=100)
    consequence_of_delay: int = Field(default=50, ge=0, le=100)
    duration_minutes: int = Field(default=30, ge=5, le=1440)
    timezone: str = "America/Toronto"
    due_at: datetime | None = None


class TaskCreate(TaskBase):
    source_system: str = Field(default="direct", min_length=1, max_length=64)
    source_id: str | None = Field(default=None, max_length=255)


class TaskSync(TaskBase):
    source_system: str = Field(min_length=1, max_length=64)
    source_id: str = Field(min_length=1, max_length=255)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    source_url: str | None = None
    source_revision: str | None = None
    notes_snapshot: str | None = None
    category: TaskCategory | None = None
    execution_policy: ExecutionPolicy | None = None
    priority: int | None = Field(default=None, ge=0, le=100)
    consequence_of_delay: int | None = Field(default=None, ge=0, le=100)
    duration_minutes: int | None = Field(default=None, ge=5, le=1440)
    timezone: str | None = None
    due_at: datetime | None = None
    status: TaskStatus | None = None
    expected_version: int | None = Field(default=None, ge=1)


class TaskRead(TaskBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_system: str
    source_id: str
    status: TaskStatus
    attempt_count: int
    miss_count: int
    version: int
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class CalendarBindingCreate(BaseModel):
    provider: str = "google_calendar"
    calendar_id: str = Field(min_length=1, max_length=255)
    event_id: str = Field(min_length=1, max_length=255)
    scheduled_start: datetime
    scheduled_end: datetime

    @model_validator(mode="after")
    def validate_window(self) -> "CalendarBindingCreate":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        return self


class CalendarBindingRead(CalendarBindingCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    followup_due_at: datetime
    followup_status: str
    followup_handled_at: datetime | None


class FollowupDue(BaseModel):
    binding: CalendarBindingRead
    task: TaskRead


class FollowupResolve(BaseModel):
    result: AttemptResult
    note: str | None = None


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    ordinal: int
    result: AttemptResult
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    note: str | None
    created_at: datetime


class FollowupResolution(BaseModel):
    task: TaskRead
    attempt: AttemptRead
    binding: CalendarBindingRead


class CandidateWindow(BaseModel):
    start: datetime
    end: datetime

    @model_validator(mode="after")
    def validate_window(self) -> "CandidateWindow":
        if self.end <= self.start:
            raise ValueError("end must be after start")
        return self


class PlanningRequest(BaseModel):
    candidate_windows: list[CandidateWindow] = Field(min_length=1, max_length=100)
    now: datetime | None = None


class ScoreBreakdown(BaseModel):
    urgency: float
    consequence: float
    sooner: float
    retry_pressure: float
    deadline: float
    time_fit: float
    total: float


class PlanningRecommendation(BaseModel):
    recommended: CandidateWindow | None
    requires_review: bool
    reason: str
    score: ScoreBreakdown | None = None


class OrchestrationCommandSubmit(BaseModel):
    """A single AI decision handed to deterministic workers exactly once."""

    command_key: str = Field(min_length=1, max_length=255)
    command_type: OrchestrationCommandType
    expected_task_version: int | None = Field(default=None, ge=1)
    requested_by: str = Field(default="chatgpt", min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)
    desired_start: datetime | None = None
    desired_end: datetime | None = None
    follow_up_at: datetime | None = None
    follow_up_date: date | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_command(self) -> "OrchestrationCommandSubmit":
        needs_window = self.command_type in {
            OrchestrationCommandType.RESCHEDULE,
            OrchestrationCommandType.STATUS_CHECK,
        }
        if needs_window and (self.desired_start is None or self.desired_end is None):
            raise ValueError(f"{self.command_type.value} requires desired_start and desired_end")
        if self.desired_start is not None or self.desired_end is not None:
            if self.desired_start is None or self.desired_end is None:
                raise ValueError("desired_start and desired_end must be provided together")
            if self.desired_end <= self.desired_start:
                raise ValueError("desired_end must be after desired_start")
        if self.command_type == OrchestrationCommandType.WAIT:
            if self.follow_up_at is None and self.follow_up_date is None:
                raise ValueError("wait requires follow_up_at or follow_up_date")
            if self.follow_up_at is not None and self.follow_up_date is not None:
                raise ValueError("wait accepts one follow-up granularity, not both")
        elif self.follow_up_at is not None or self.follow_up_date is not None:
            raise ValueError("follow_up_at/follow_up_date are only valid for wait")
        return self


class OrchestrationCommandComplete(BaseModel):
    success: bool
    result: dict[str, object] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_completion(self) -> "OrchestrationCommandComplete":
        if self.success and self.error is not None:
            raise ValueError("successful command completion cannot include error")
        if not self.success and not self.error:
            raise ValueError("failed command completion requires error")
        return self


class OrchestrationCommandRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    command_key: str
    command_type: OrchestrationCommandType
    status: OrchestrationCommandStatus
    expected_task_version: int | None
    requested_by: str
    payload: dict[str, object]
    result_payload: dict[str, object] | None
    failure_reason: str | None
    created_at: datetime
    completed_at: datetime | None


class CommandEffectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    command_id: str
    effect_key: str
    ordinal: int
    target: str
    operation: str
    status: CommandEffectStatus
    request_payload: dict[str, object]
    result_payload: dict[str, object] | None
    attempt_count: int
    next_attempt_at: datetime | None
    lease_owner: str | None
    lease_until: datetime | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class WorkerRunRequest(BaseModel):
    worker_id: str | None = Field(default=None, min_length=1, max_length=128)
    max_commands: int = Field(default=20, ge=1, le=100)


class WorkerRunResult(BaseModel):
    worker_id: str
    commands_seen: int
    effects_applied: int
    effects_retried: int
    commands_completed: int
    commands_failed: int


class OutboxEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    idempotency_key: str
    payload: dict[str, object]
    status: str
    created_at: datetime
    published_at: datetime | None
