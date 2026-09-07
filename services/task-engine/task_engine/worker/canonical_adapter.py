from __future__ import annotations

import uuid
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from task_engine.worker.adapters import (
    CanonicalNeonAdapter as BaseCanonicalNeonAdapter,
    EffectEnvelope,
    PermanentEffectError,
    RetryableEffectError,
    _iso_datetime,
)


class CanonicalNeonAdapter(BaseCanonicalNeonAdapter):
    """Production canonical adapter using guarded binding-replacement functions."""

    ALLOWED_SOURCE_SYSTEMS = {
        "neon",
        "llm4life",
        "llm4life_actions",
        "neon_llm4life",
    }

    def _reschedule(
        self,
        conn: psycopg.Connection[Any],
        envelope: EffectEnvelope,
        action_id: uuid.UUID,
    ) -> dict[str, Any]:
        start = _iso_datetime(envelope.command_payload.get("desired_start"))
        end = _iso_datetime(envelope.command_payload.get("desired_end"))
        if start is None or end is None:
            raise PermanentEffectError("Reschedule requires desired_start and desired_end")
        duration = max(1, round((end - start).total_seconds() / 60))
        scheduled = self._one(
            conn,
            "SELECT * FROM llm4life.schedule_action(%s,%s,%s)",
            (action_id, start, duration),
        )
        calendar = envelope.prior_results.get("calendar.ensure_execution")
        if not calendar or not calendar.get("event_id") or not calendar.get("calendar_id"):
            raise RetryableEffectError("Calendar execution result is not available for canonical binding")
        event_id = str(calendar["event_id"])
        calendar_id = str(calendar["calendar_id"])
        binding = self._one(
            conn,
            "SELECT * FROM llm4life.replace_calendar_execution_binding(%s,%s,%s,%s)",
            (
                action_id,
                event_id,
                calendar_id,
                Jsonb(
                    {
                        "command_key": envelope.command_key,
                        "scheduled_start": start.isoformat(),
                        "scheduled_end": end.isoformat(),
                    }
                ),
            ),
        )
        return {"scheduled": scheduled, "binding": binding}

    @staticmethod
    def _archive_execution_bindings(
        conn: psycopg.Connection[Any],
        action_id: uuid.UUID,
        *,
        except_event_id: str | None = None,
    ) -> None:
        if except_event_id is not None:
            # Replacement must be atomic; callers with a replacement event use _reschedule.
            raise PermanentEffectError(
                "Execution binding replacement must use replace_calendar_execution_binding"
            )
        conn.execute(
            "SELECT llm4life.archive_action_execution_bindings(%s)",
            (action_id,),
        )
