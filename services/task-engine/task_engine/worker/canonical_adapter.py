from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from task_engine.worker.adapters import (
    CanonicalNeonAdapter as BaseCanonicalNeonAdapter,
)
from task_engine.worker.adapters import (
    EffectEnvelope,
    PermanentEffectError,
    RetryableEffectError,
    _iso_datetime,
    _metadata,
)


class CanonicalNeonAdapter(BaseCanonicalNeonAdapter):
    """Production canonical adapter using guarded binding-replacement functions."""

    ALLOWED_SOURCE_SYSTEMS = {
        "neon",
        "llm4life",
        "llm4life_actions",
        "neon_llm4life",
    }

    @staticmethod
    def _is_recurring(envelope: EffectEnvelope) -> bool:
        metadata = _metadata(envelope)
        return bool(metadata.get("template_id") and metadata.get("occurrence_key"))

    @staticmethod
    def _recurring_identity(
        envelope: EffectEnvelope,
    ) -> tuple[uuid.UUID, str, Any, Any, str | None]:
        metadata = _metadata(envelope)
        try:
            template_id = uuid.UUID(str(metadata["template_id"]))
        except (KeyError, ValueError) as exc:
            raise PermanentEffectError("Recurring command requires a valid template_id") from exc
        occurrence_key = str(metadata.get("occurrence_key") or "").strip()
        occurrence_start = _iso_datetime(metadata.get("occurrence_start"))
        occurrence_end = _iso_datetime(metadata.get("occurrence_end"))
        if not occurrence_key or occurrence_start is None or occurrence_end is None:
            raise PermanentEffectError(
                "Recurring command requires occurrence_key, occurrence_start, and occurrence_end"
            )
        event_ref = metadata.get("calendar_event_id")
        return (
            template_id,
            occurrence_key,
            occurrence_start,
            occurrence_end,
            str(event_ref) if event_ref else None,
        )

    def _reschedule(
        self,
        conn: psycopg.Connection[Any],
        envelope: EffectEnvelope,
        action_id: uuid.UUID,
    ) -> dict[str, Any]:
        if self._is_recurring(envelope):
            raise PermanentEffectError(
                "Recurring occurrences cannot use reschedule; use an occurrence-specific recovery path"
            )
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
            raise RetryableEffectError(
                "Calendar execution result is not available for canonical binding"
            )
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
        if not binding:
            raise PermanentEffectError("Canonical execution binding replacement returned no row")
        return {"scheduled": scheduled, "binding": binding}

    def _wait(
        self,
        conn: psycopg.Connection[Any],
        envelope: EffectEnvelope,
        action_id: uuid.UUID,
    ) -> dict[str, Any]:
        if not self._is_recurring(envelope):
            return super()._wait(conn, envelope, action_id)
        template_id, key, start, end, event_ref = self._recurring_identity(envelope)
        row = self._one(
            conn,
            "SELECT * FROM llm4life.upsert_action_instance(%s,%s,%s,%s,%s,%s,%s)",
            (
                template_id,
                key,
                start,
                end,
                event_ref,
                "waiting",
                Jsonb({"command_key": envelope.command_key}),
            ),
        )
        if not row:
            raise PermanentEffectError("Recurring waiting occurrence could not be upserted")
        self._record_execution(conn, envelope, action_id, "waiting", datetime.now(UTC))
        return {"mode": "recurring_occurrence", **row}

    def _cancel(
        self,
        conn: psycopg.Connection[Any],
        envelope: EffectEnvelope,
        action_id: uuid.UUID,
    ) -> dict[str, Any]:
        if not self._is_recurring(envelope):
            return super()._cancel(conn, envelope, action_id)
        template_id, key, start, end, event_ref = self._recurring_identity(envelope)
        row = self._one(
            conn,
            "SELECT * FROM llm4life.upsert_action_instance(%s,%s,%s,%s,%s,%s,%s)",
            (
                template_id,
                key,
                start,
                end,
                event_ref,
                "cancelled",
                Jsonb({"command_key": envelope.command_key}),
            ),
        )
        if not row:
            raise PermanentEffectError("Recurring cancelled occurrence could not be upserted")
        self._record_execution(conn, envelope, action_id, "cancelled", datetime.now(UTC))
        return {"mode": "recurring_occurrence", **row}

    def _defer(
        self,
        conn: psycopg.Connection[Any],
        envelope: EffectEnvelope,
        action_id: uuid.UUID,
    ) -> dict[str, Any]:
        if self._is_recurring(envelope):
            raise PermanentEffectError(
                "Recurring occurrence defer requires the planning-review/recovery protocol"
            )
        return super()._defer(conn, envelope, action_id)

    @staticmethod
    def _archive_execution_bindings(
        conn: psycopg.Connection[Any],
        action_id: uuid.UUID,
        *,
        except_event_id: str | None = None,
    ) -> None:
        if except_event_id is not None:
            raise PermanentEffectError(
                "Execution binding replacement must use replace_calendar_execution_binding"
            )
        conn.execute(
            "SELECT llm4life.archive_action_execution_bindings(%s)",
            (action_id,),
        )
