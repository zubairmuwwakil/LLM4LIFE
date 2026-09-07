from __future__ import annotations

from typing import Any

from task_engine.worker.adapters import EffectEnvelope, GoogleCalendarAdapter as BaseGoogleCalendarAdapter, _metadata


class GoogleCalendarAdapter(BaseGoogleCalendarAdapter):
    """Production Calendar adapter with safe no-op presentation for unbound tasks."""

    def _mark_presentation(self, envelope: EffectEnvelope) -> dict[str, Any]:
        metadata = _metadata(envelope)
        binding = self._latest_binding(envelope)
        if not metadata.get("calendar_event_id") and binding is None:
            return {"applied": False, "reason": "no_calendar_binding"}
        return super()._mark_presentation(envelope)
