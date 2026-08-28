from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from task_engine.enums import AttemptResult, ExecutionPolicy, TaskCategory, TaskStatus


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
