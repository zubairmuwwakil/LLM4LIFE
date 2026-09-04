from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from task_engine.config import Settings
from task_engine.enums import ExecutionPolicy
from task_engine.models import Task
from task_engine.schemas import CandidateWindow, PlanningRecommendation, ScoreBreakdown


@dataclass(frozen=True)
class CandidateScore:
    window: CandidateWindow
    breakdown: ScoreBreakdown


class Planner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def recommend(
        self,
        task: Task,
        windows: list[CandidateWindow],
        now: datetime | None = None,
    ) -> PlanningRecommendation:
        now = self._ensure_aware(now or datetime.now(UTC))

        if task.execution_policy == ExecutionPolicy.FIXED.value:
            return PlanningRecommendation(
                recommended=None,
                requires_review=True,
                reason="Fixed tasks are never auto-rescheduled.",
            )

        if self._should_stop_auto_rescheduling(task):
            return PlanningRecommendation(
                recommended=None,
                requires_review=True,
                reason="Repeated misses are behavioral evidence; planner review is required.",
            )

        scored: list[CandidateScore] = []
        for window in windows:
            score = self._score_window(task, window, now)
            if score is not None:
                scored.append(score)

        if not scored:
            return PlanningRecommendation(
                recommended=None,
                requires_review=True,
                reason="No candidate window satisfies the task constraints.",
            )

        best = max(scored, key=lambda item: item.breakdown.total)
        return PlanningRecommendation(
            recommended=best.window,
            requires_review=False,
            reason="Selected the highest-scoring realistic execution window.",
            score=best.breakdown,
        )

    def _should_stop_auto_rescheduling(self, task: Task) -> bool:
        high_stakes = max(task.priority, task.consequence_of_delay) >= self.settings.high_stakes_threshold
        return task.miss_count >= self.settings.misses_before_review and not high_stakes

    def _score_window(
        self, task: Task, window: CandidateWindow, now: datetime
    ) -> CandidateScore | None:
        start = self._ensure_aware(window.start)
        end = self._ensure_aware(window.end)
        duration = (end - start).total_seconds() / 60
        if start < now or duration < task.duration_minutes:
            return None

        horizon_end = now + timedelta(days=self.settings.auto_reschedule_horizon_days)
        if start > horizon_end:
            return None

        tz = ZoneInfo(task.timezone or self.settings.timezone)
        local_start = start.astimezone(tz)
        local_end = end.astimezone(tz)
        if not self._inside_default_movable_window(local_start, local_end):
            return None

        days_ahead = max(0.0, (start - now).total_seconds() / 86400)
        urgency = task.priority * 0.30
        consequence = task.consequence_of_delay * 0.30
        sooner = max(0.0, 25.0 - days_ahead * 4.0)
        retry_pressure = min(15.0, task.miss_count * 4.0)
        deadline = self._deadline_score(task, start)
        time_fit = self._time_fit(local_start)
        total = urgency + consequence + sooner + retry_pressure + deadline + time_fit

        return CandidateScore(
            window=window,
            breakdown=ScoreBreakdown(
                urgency=round(urgency, 2),
                consequence=round(consequence, 2),
                sooner=round(sooner, 2),
                retry_pressure=round(retry_pressure, 2),
                deadline=round(deadline, 2),
                time_fit=round(time_fit, 2),
                total=round(total, 2),
            ),
        )

    def _inside_default_movable_window(self, start: datetime, end: datetime) -> bool:
        if start.date() != end.date():
            return False
        start_minutes = start.hour * 60 + start.minute
        end_minutes = end.hour * 60 + end.minute
        allowed_start = self.settings.movable_window_start_hour * 60
        allowed_end = self.settings.movable_window_end_hour * 60
        return start_minutes >= allowed_start and end_minutes <= allowed_end

    @staticmethod
    def _deadline_score(task: Task, candidate_start: datetime) -> float:
        if task.due_at is None:
            return 0.0
        due_at = Planner._ensure_aware(task.due_at)
        hours_until_due = (due_at - candidate_start).total_seconds() / 3600
        if hours_until_due < 0:
            return -50.0
        if hours_until_due <= 24:
            return 25.0
        if hours_until_due <= 72:
            return 15.0
        return 5.0

    def _time_fit(self, local_start: datetime) -> float:
        midpoint = (self.settings.movable_window_start_hour + self.settings.movable_window_end_hour) / 2
        distance = abs((local_start.hour + local_start.minute / 60) - midpoint)
        return max(0.0, 10.0 - distance * 2.0)

    @staticmethod
    def _ensure_aware(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value
