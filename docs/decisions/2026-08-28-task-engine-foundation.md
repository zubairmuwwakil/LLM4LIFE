# 2026-08-28 — Add a task execution coordination engine

**Status:** Proposed implementation ready for review; not deployed yet.

## Decision

Introduce a small LLM4LIFE Task Engine for **cross-system execution lifecycle state**.

This refines, rather than replaces, the existing ownership model:

- Things 3 remains canonical for personal backlog/actions.
- Jira remains canonical for engineering backlog/work.
- Google Calendar remains canonical for scheduled execution/time.
- AI remains the reasoning/routing/planning layer.
- Task Engine owns only cross-system coordination metadata: stable source identity, execution attempts/misses, Calendar event bindings, follow-up due state, idempotency, reschedule/review state, and a durable event outbox.

## Why

The existing Calendar follow-up watcher must infer whether events are task-style work. A user-owned task can look structurally like a meeting, and an hourly watcher that searches for events ending "about an hour ago" has an inherently fuzzy boundary. One missed follow-up demonstrated that these heuristics are not strong enough for a reliable personal operating system.

Calendar titles/descriptions are also the wrong place to encode durable lifecycle state and retry history.

## New invariant

Whenever a task is deliberately scheduled for execution, create an explicit binding:

```text
canonical source item -> task_engine_id -> exact calendar_event_id
```

The Task Engine calculates an explicit `followup_due_at`. Follow-up workers query due bindings rather than rediscovering task events heuristically.

## Rescheduling rule

A miss increments durable evidence. Movable work can be proposed for a realistic future slot, but repeated low-stakes misses stop automatic rescheduling and require planner reassessment. Fixed/external commitments are never auto-moved by this service.

## Vendor independence

The service deliberately contains no LLM dependency. It exposes a narrow HTTP API and durable outbox so ChatGPT, Claude, OpenClaw, a local LLM, Slack/Discord consumers, or future orchestrators can use the same lifecycle state.

## Security boundary

Generic implementation code may live in this public repository. Runtime databases, secrets, private task content exports, credentials, tokens, and private Calendar/message data must never be committed.

The first version avoids introducing a second broad Google OAuth credential path. Existing authorized orchestration layers supply Calendar event IDs and candidate free windows.

## Rollout

1. Patch the current Calendar watcher as a temporary compatibility layer.
2. Deploy Task Engine privately and shadow new execution blocks.
3. Switch follow-ups to explicit Task Engine due bindings after observed reliability.
4. Add only thin canonical-source adapters that prove useful.
5. Keep notification consumers replaceable through the outbox.

## Supersedes / clarifies

This does **not** supersede `backlog_is_not_calendar` or the existing canonical ownership rules. It clarifies that the AI orchestration layer may use a purpose-built coordination-state service without making that service a second backlog database.
