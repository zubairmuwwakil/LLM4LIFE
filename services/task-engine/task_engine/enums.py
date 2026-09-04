from enum import StrEnum


class TaskStatus(StrEnum):
    OPEN = "open"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    NEEDS_RESCHEDULE = "needs_reschedule"
    NEEDS_REVIEW = "needs_review"
    CANCELLED = "cancelled"


class ExecutionPolicy(StrEnum):
    MOVABLE = "movable"
    FIXED = "fixed"


class TaskCategory(StrEnum):
    WORK_LEARNING = "work_learning"
    HEALTH_ROUTINE = "health_routine"
    ADMIN_MONEY = "admin_money"
    PERSONAL_LIFE = "personal_life"
    PLANNING_INFO = "planning_info"
    CRITICAL = "critical"


class AttemptResult(StrEnum):
    COMPLETED = "completed"
    MISSED = "missed"
    SKIPPED = "skipped"


class FollowupStatus(StrEnum):
    PENDING = "pending"
    HANDLED = "handled"
    CANCELLED = "cancelled"


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PUBLISHED = "published"
