from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from urllib.parse import quote

import httpx
import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from task_engine.config import Settings


class RetryableEffectError(RuntimeError):
    """A side effect failed transiently and is safe to retry with the same effect key."""


class PermanentEffectError(RuntimeError):
    """A side effect cannot be made safe by retrying unchanged input."""


@dataclass(frozen=True)
class EffectEnvelope:
    effect_id: str
    effect_key: str
    target: str
    operation: str
    command_id: str
    command_key: str
    command_type: str
    command_payload: dict[str, Any]
    task_id: str
    source_system: str
    source_id: str
    title: str
    category: str
    duration_minutes: int
    timezone: str
    bindings: tuple[dict[str, Any], ...]
    prior_results: dict[str, dict[str, Any]]


class EffectAdapter(Protocol):
    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]: ...


def _metadata(envelope: EffectEnvelope) -> dict[str, Any]:
    value = envelope.command_payload.get("metadata")
    return dict(value) if isinstance(value, dict) else {}


def _iso_datetime(value: object | None) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise PermanentEffectError(f"Expected datetime string, received {type(value).__name__}")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise PermanentEffectError("Datetime values must include a timezone")
    return parsed


def _iso_date(value: object | None) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise PermanentEffectError(f"Expected date string, received {type(value).__name__}")
    return date.fromisoformat(value)


class GoogleCalendarAdapter:
    """Narrow Google Calendar adapter with command-key idempotency markers.

    Calendar creation is at-least-once at the transport layer but effectively idempotent:
    retries first search for the private command marker before creating a new event.
    Existing bound events are patched in place.
    """

    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        self.settings = settings
        self.client = client or httpx.Client(timeout=20.0)

    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]:
        if envelope.operation == "ensure_execution":
            return self._ensure_execution(envelope, status_check=False)
        if envelope.operation == "ensure_status_check":
            return self._ensure_execution(envelope, status_check=True)
        if envelope.operation in {
            "mark_completed",
            "mark_waiting",
            "mark_cancelled",
            "mark_deferred",
        }:
            return self._mark_presentation(envelope)
        raise PermanentEffectError(f"Unsupported Calendar operation: {envelope.operation}")

    def _require_credentials(self) -> None:
        missing = [
            name
            for name, value in {
                "GOOGLE_CLIENT_ID": self.settings.google_client_id,
                "GOOGLE_CLIENT_SECRET": self.settings.google_client_secret,
                "GOOGLE_REFRESH_TOKEN": self.settings.google_refresh_token,
            }.items()
            if not value
        ]
        if missing:
            raise PermanentEffectError(
                "Calendar adapter is not configured; missing " + ", ".join(missing)
            )

    def _access_token(self) -> str:
        self._require_credentials()
        response = self.client.post(
            self.settings.google_oauth_token_url,
            data={
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "refresh_token": self.settings.google_refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        if response.status_code >= 500 or response.status_code == 429:
            raise RetryableEffectError(f"Google token refresh transient failure: {response.status_code}")
        if not response.is_success:
            raise PermanentEffectError(f"Google token refresh failed: {response.status_code}")
        token = response.json().get("access_token")
        if not token:
            raise PermanentEffectError("Google token refresh returned no access_token")
        return str(token)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = self._access_token()
        response = self.client.request(
            method,
            f"{self.settings.google_calendar_api_base}{path}",
            params=params,
            json=json,
            headers={"authorization": f"Bearer {token}", "content-type": "application/json"},
        )
        if response.status_code >= 500 or response.status_code == 429:
            raise RetryableEffectError(f"Google Calendar transient failure: {response.status_code}")
        if response.status_code in {401, 403}:
            raise PermanentEffectError(
                f"Google Calendar authorization failed: {response.status_code}; Calendar scope may be missing"
            )
        if response.status_code == 404:
            return {"_not_found": True}
        if not response.is_success:
            raise PermanentEffectError(
                f"Google Calendar request failed: {response.status_code} {response.text[:500]}"
            )
        if response.status_code == 204 or not response.content:
            return {}
        body = response.json()
        return dict(body) if isinstance(body, dict) else {"value": body}

    @staticmethod
    def _latest_binding(envelope: EffectEnvelope) -> dict[str, Any] | None:
        if not envelope.bindings:
            return None
        return max(envelope.bindings, key=lambda item: str(item.get("scheduled_end") or ""))

    def _calendar_id(self, envelope: EffectEnvelope) -> str:
        metadata = _metadata(envelope)
        explicit = metadata.get("calendar_id")
        if explicit:
            return str(explicit)
        binding = self._latest_binding(envelope)
        if binding and binding.get("calendar_id"):
            return str(binding["calendar_id"])
        raise PermanentEffectError(
            "Calendar operation requires metadata.calendar_id when no existing binding exists"
        )

    def _find_by_marker(self, calendar_id: str, command_key: str) -> list[dict[str, Any]]:
        body = self._request(
            "GET",
            f"/calendars/{quote(calendar_id, safe='')}/events",
            params={
                "privateExtendedProperty": f"llm4lifeCommandKey={command_key}",
                "singleEvents": "true",
                "maxResults": "3",
            },
        )
        items = body.get("items", [])
        return [dict(item) for item in items] if isinstance(items, list) else []

    def _ensure_execution(self, envelope: EffectEnvelope, *, status_check: bool) -> dict[str, Any]:
        start = _iso_datetime(envelope.command_payload.get("desired_start"))
        end = _iso_datetime(envelope.command_payload.get("desired_end"))
        if start is None or end is None:
            raise PermanentEffectError("Calendar execution effect requires desired_start and desired_end")
        calendar_id = self._calendar_id(envelope)
        binding = None if status_check else self._latest_binding(envelope)
        metadata = _metadata(envelope)
        marker = f"[LLM4LIFE:COMMAND_KEY={envelope.command_key}]"
        action_marker = metadata.get("canonical_action_id") or envelope.source_id
        description_parts = [marker, f"[LLM4LIFE:ACTION_ID={action_marker}]"]
        if metadata.get("occurrence_key"):
            description_parts.append(
                f"[LLM4LIFE:RECOVERY_FOR_OCCURRENCE={metadata['occurrence_key']}]"
            )
        if metadata.get("series_external_id"):
            description_parts.append(
                f"[LLM4LIFE:RECOVERY_FOR_SERIES={metadata['series_external_id']}]"
            )
        if envelope.command_payload.get("reason"):
            description_parts.append(str(envelope.command_payload["reason"]))
        summary = (
            f"Check status — {envelope.title}"
            if status_check
            else str(metadata.get("calendar_title") or envelope.title)
        )
        event = {
            "summary": summary,
            "description": "\n".join(description_parts),
            "start": {"dateTime": start.isoformat(), "timeZone": envelope.timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": envelope.timezone},
            "extendedProperties": {
                "private": {
                    "llm4lifeCommandKey": envelope.command_key,
                    "llm4lifeTaskId": envelope.task_id,
                    "llm4lifeActionId": str(action_marker),
                    "llm4lifeCommandType": envelope.command_type,
                }
            },
        }

        if binding and binding.get("event_id"):
            event_id = str(binding["event_id"])
            updated = self._request(
                "PATCH",
                f"/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
                json=event,
            )
            if not updated.get("_not_found"):
                return self._event_result(calendar_id, updated, start, end, reused=True)

        matches = self._find_by_marker(calendar_id, envelope.command_key)
        if len(matches) > 1:
            raise PermanentEffectError(
                f"Duplicate Calendar command marker detected for {envelope.command_key}"
            )
        if len(matches) == 1:
            existing = matches[0]
            event_id = str(existing["id"])
            updated = self._request(
                "PATCH",
                f"/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
                json=event,
            )
            return self._event_result(calendar_id, updated, start, end, reused=True)

        created = self._request(
            "POST",
            f"/calendars/{quote(calendar_id, safe='')}/events",
            json=event,
        )
        return self._event_result(calendar_id, created, start, end, reused=False)

    @staticmethod
    def _event_result(
        calendar_id: str,
        event: dict[str, Any],
        start: datetime,
        end: datetime,
        *,
        reused: bool,
    ) -> dict[str, Any]:
        event_id = event.get("id")
        if not event_id:
            raise RetryableEffectError("Calendar write returned no event id")
        return {
            "applied": True,
            "calendar_id": calendar_id,
            "event_id": str(event_id),
            "html_link": event.get("htmlLink"),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "reused": reused,
        }

    def _mark_presentation(self, envelope: EffectEnvelope) -> dict[str, Any]:
        metadata = _metadata(envelope)
        calendar_id = self._calendar_id(envelope)
        explicit_event = metadata.get("calendar_event_id")
        binding = self._latest_binding(envelope)
        event_id = str(explicit_event or (binding or {}).get("event_id") or "")
        if not event_id:
            return {"applied": False, "reason": "no_calendar_binding"}
        current = self._request(
            "GET",
            f"/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
        )
        if current.get("_not_found"):
            return {"applied": False, "reason": "bound_event_not_found", "event_id": event_id}
        prefixes = {
            "mark_completed": "✅ Completed — ",
            "mark_waiting": "⏳ Waiting — ",
            "mark_cancelled": "🚫 Cancelled — ",
            "mark_deferred": "↪ Deferred — ",
        }
        prefix = prefixes[envelope.operation]
        old_summary = str(current.get("summary") or envelope.title)
        for known in prefixes.values():
            if old_summary.startswith(known):
                old_summary = old_summary[len(known) :]
                break
        private = dict(((current.get("extendedProperties") or {}).get("private") or {}))
        private.update(
            {
                "llm4lifeCommandKey": envelope.command_key,
                "llm4lifeTaskId": envelope.task_id,
                "llm4lifeCommandType": envelope.command_type,
            }
        )
        updated = self._request(
            "PATCH",
            f"/calendars/{quote(calendar_id, safe='')}/events/{quote(event_id, safe='')}",
            json={
                "summary": prefix + old_summary,
                "extendedProperties": {"private": private},
            },
        )
        if updated.get("_not_found"):
            return {"applied": False, "reason": "bound_event_not_found", "event_id": event_id}
        return {"applied": True, "calendar_id": calendar_id, "event_id": event_id}


class CanonicalNeonAdapter:
    """Canonical-state adapter restricted to approved llm4life functions and safe views."""

    ALLOWED_SOURCE_SYSTEMS = {"neon", "llm4life", "llm4life_actions"}

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def apply(self, envelope: EffectEnvelope) -> dict[str, Any]:
        if not self.settings.canonical_database_url:
            raise PermanentEffectError("TASK_ENGINE_CANONICAL_DATABASE_URL is not configured")
        action_id = self._action_id(envelope)
        url = self.settings.canonical_database_url.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        try:
            with psycopg.connect(url, row_factory=dict_row) as conn:
                if envelope.operation == "complete":
                    result = self._complete(conn, envelope, action_id)
                elif envelope.operation == "reschedule":
                    result = self._reschedule(conn, envelope, action_id)
                elif envelope.operation == "wait":
                    result = self._wait(conn, envelope, action_id)
                elif envelope.operation == "cancel":
                    result = self._cancel(conn, envelope, action_id)
                elif envelope.operation == "defer":
                    result = self._defer(conn, envelope, action_id)
                elif envelope.operation == "bind_status_check":
                    result = self._bind_status_check(conn, envelope, action_id)
                else:
                    raise PermanentEffectError(
                        f"Unsupported canonical operation: {envelope.operation}"
                    )
                self._receipt(conn, envelope, action_id, result)
                return result
        except PermanentEffectError:
            raise
        except (psycopg.OperationalError, psycopg.InterfaceError) as exc:
            raise RetryableEffectError(f"Canonical Neon transport failure: {exc}") from exc
        except psycopg.Error as exc:
            # SQL/function contract errors should not be hammered indefinitely.
            raise PermanentEffectError(f"Canonical Neon function failed: {exc}") from exc

    def _action_id(self, envelope: EffectEnvelope) -> uuid.UUID:
        metadata = _metadata(envelope)
        raw = metadata.get("canonical_action_id")
        if raw is None:
            if envelope.source_system not in self.ALLOWED_SOURCE_SYSTEMS:
                raise PermanentEffectError(
                    "Canonical action id must be supplied for non-Neon Task Engine sources"
                )
            raw = envelope.source_id
        try:
            return uuid.UUID(str(raw))
        except ValueError as exc:
            raise PermanentEffectError(f"Invalid canonical action UUID: {raw}") from exc

    @staticmethod
    def _one(conn: psycopg.Connection[Any], sql: str, params: tuple[Any, ...]) -> dict[str, Any]:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else {}

    def _complete(
        self, conn: psycopg.Connection[Any], envelope: EffectEnvelope, action_id: uuid.UUID
    ) -> dict[str, Any]:
        metadata = _metadata(envelope)
        completed_at = _iso_datetime(metadata.get("completed_at")) or datetime.now(UTC)
        if metadata.get("template_id") and metadata.get("occurrence_key"):
            template_id = uuid.UUID(str(metadata["template_id"]))
            occurrence_start = _iso_datetime(metadata.get("occurrence_start"))
            occurrence_end = _iso_datetime(metadata.get("occurrence_end"))
            if occurrence_start is None or occurrence_end is None:
                raise PermanentEffectError(
                    "Recurring completion requires occurrence_start and occurrence_end"
                )
            row = self._one(
                conn,
                "SELECT * FROM llm4life.upsert_action_instance(%s,%s,%s,%s,%s,%s,%s)",
                (
                    template_id,
                    str(metadata["occurrence_key"]),
                    occurrence_start,
                    occurrence_end,
                    metadata.get("calendar_event_id"),
                    "done",
                    Jsonb({"command_key": envelope.command_key, "completed_at": completed_at.isoformat()}),
                ),
            )
            result: dict[str, Any] = {"mode": "recurring_occurrence", **row}
        else:
            row = self._one(
                conn,
                "SELECT * FROM llm4life.mark_action_done(%s,%s)",
                (action_id, completed_at),
            )
            result = {"mode": "non_recurring", **row}
            self._archive_execution_bindings(conn, action_id)
        self._record_execution(conn, envelope, action_id, "done", completed_at)
        return result

    def _reschedule(
        self, conn: psycopg.Connection[Any], envelope: EffectEnvelope, action_id: uuid.UUID
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
        self._archive_execution_bindings(conn, action_id, except_event_id=event_id)
        binding = self._one(
            conn,
            "SELECT * FROM llm4life.bind_calendar_event(%s,%s,%s,%s,%s)",
            (
                action_id,
                event_id,
                calendar_id,
                "execution_binding",
                Jsonb({
                    "command_key": envelope.command_key,
                    "scheduled_start": start.isoformat(),
                    "scheduled_end": end.isoformat(),
                }),
            ),
        )
        return {"scheduled": scheduled, "binding": binding}

    def _wait(
        self, conn: psycopg.Connection[Any], envelope: EffectEnvelope, action_id: uuid.UUID
    ) -> dict[str, Any]:
        follow_up_at = _iso_datetime(envelope.command_payload.get("follow_up_at"))
        follow_up_date = _iso_date(envelope.command_payload.get("follow_up_date"))
        if follow_up_at is None and follow_up_date is None:
            raise PermanentEffectError("Waiting requires follow_up_at or follow_up_date")
        row = self._one(
            conn,
            "SELECT * FROM llm4life.mark_action_waiting(%s,%s,%s)",
            (action_id, follow_up_at, follow_up_date),
        )
        self._archive_execution_bindings(conn, action_id)
        self._record_execution(conn, envelope, action_id, "waiting", datetime.now(UTC))
        return row

    def _cancel(
        self, conn: psycopg.Connection[Any], envelope: EffectEnvelope, action_id: uuid.UUID
    ) -> dict[str, Any]:
        completed_at = datetime.now(UTC)
        row = self._one(
            conn,
            "SELECT * FROM llm4life.cancel_action(%s,%s)",
            (action_id, completed_at),
        )
        self._archive_execution_bindings(conn, action_id)
        self._record_execution(conn, envelope, action_id, "cancelled", completed_at)
        return row

    def _defer(
        self, conn: psycopg.Connection[Any], envelope: EffectEnvelope, action_id: uuid.UUID
    ) -> dict[str, Any]:
        row = self._one(conn, "SELECT * FROM llm4life.mark_action_next(%s)", (action_id,))
        self._archive_execution_bindings(conn, action_id)
        return row

    def _bind_status_check(
        self, conn: psycopg.Connection[Any], envelope: EffectEnvelope, action_id: uuid.UUID
    ) -> dict[str, Any]:
        calendar = envelope.prior_results.get("calendar.ensure_status_check")
        if not calendar or not calendar.get("event_id") or not calendar.get("calendar_id"):
            raise RetryableEffectError("Status-check Calendar result is not available")
        return self._one(
            conn,
            "SELECT * FROM llm4life.bind_calendar_event(%s,%s,%s,%s,%s)",
            (
                action_id,
                str(calendar["event_id"]),
                str(calendar["calendar_id"]),
                "status_check",
                Jsonb({"command_key": envelope.command_key}),
            ),
        )

    @staticmethod
    def _archive_execution_bindings(
        conn: psycopg.Connection[Any],
        action_id: uuid.UUID,
        *,
        except_event_id: str | None = None,
    ) -> None:
        rows = conn.execute(
            """
            SELECT external_id, metadata->>'ref_id' AS metadata_ref_id
            FROM llm4life.action_reference_index
            WHERE action_id = %s
              AND system_id = 'google_calendar'
              AND ref_kind = 'execution_binding'
              AND archived_at IS NULL
            """,
            (action_id,),
        ).fetchall()
        # action_reference_index intentionally exposes no raw external_refs id column.
        # Only archive when the safe view carries a ref id in metadata; otherwise leave the
        # binding for reconciliation instead of reaching into canonical tables.
        for row in rows:
            if except_event_id and row["external_id"] == except_event_id:
                continue
            raw_ref_id = row.get("metadata_ref_id")
            if not raw_ref_id:
                continue
            conn.execute(
                "SELECT llm4life.archive_calendar_binding(%s)",
                (uuid.UUID(str(raw_ref_id)),),
            )

    def _record_execution(
        self,
        conn: psycopg.Connection[Any],
        envelope: EffectEnvelope,
        action_id: uuid.UUID,
        outcome: str,
        completed_at: datetime,
    ) -> None:
        metadata = _metadata(envelope)
        execution_key = str(metadata.get("execution_key") or f"command:{envelope.command_key}")
        planned_start = _iso_datetime(metadata.get("planned_start"))
        planned_duration = metadata.get("planned_duration_min")
        event_ref = metadata.get("calendar_event_id")
        conn.execute(
            "SELECT llm4life.record_action_execution(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                action_id,
                execution_key,
                outcome,
                planned_start,
                int(planned_duration) if planned_duration is not None else None,
                None,
                completed_at,
                None,
                metadata.get("context"),
                metadata.get("calendar_kind"),
                event_ref,
                envelope.command_payload.get("reason"),
                Jsonb({"command_key": envelope.command_key, "effect_key": envelope.effect_key}),
            ),
        )

    def _receipt(
        self,
        conn: psycopg.Connection[Any],
        envelope: EffectEnvelope,
        action_id: uuid.UUID,
        result: dict[str, Any],
    ) -> None:
        conn.execute(
            "SELECT llm4life.record_action_receipt(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                f"command:{envelope.command_key}:canonical:{envelope.operation}",
                f"orchestration_{envelope.operation}",
                "task_engine",
                "neon",
                "action",
                action_id,
                "completed",
                True,
                f"Applied deterministic command {envelope.command_type}: {envelope.operation}",
                envelope.task_id,
                None,
                Jsonb({"effect_key": envelope.effect_key, "result": result}),
            ),
        )
