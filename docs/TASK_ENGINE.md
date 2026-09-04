# Task Engine

_Status: implementation retained; not deployed. Ownership wording aligned with the current LLM4LIFE architecture on 2026-09-04._

## Problem

Calendar blocks are useful for execution, but Calendar is a poor place to infer durable task identity, completion state, retries, deduplication, and follow-up lifecycle. A scheduled personal action can look like a meeting, and fuzzy time-window scans can miss eligible follow-ups.

## Decision

Keep the small **Task Engine** implementation as an optional coordination-state service for scheduled execution lifecycle.

It does **not** become a second personal backlog and it does **not** replace `llm4life.actions`.

```text
Neon llm4life.actions / Jira
            |
            | stable source identity
            v
      LLM4LIFE Task Engine
   execution attempts + bindings
            |
            | exact Calendar event ID
            v
      Google Calendar
        execution time
            |
            | result / follow-up
            v
      LLM4LIFE Task Engine
            |
      AI planner / channels
```

Google Tasks remains the human-facing projection/capture client for personal actions; it is not the canonical task database.

## Ownership boundary

| Responsibility | Owner |
|---|---|
| Personal action/backlog state | Neon `llm4life.actions` |
| Human-facing personal task projection/capture | Google Tasks |
| Engineering backlog/work | Jira |
| Scheduled execution/time | Google Calendar |
| Optional cross-system execution lifecycle | Task Engine |
| Reasoning, routing, prioritization | AI orchestrator |

The Task Engine owns only coordination metadata that is useful for execution reliability: source identity, attempts/misses, Calendar bindings, due follow-ups, idempotency, execution lifecycle status, and durable domain events. It must not become a competing source of truth for action content.

## Deterministic follow-up

When a canonical action is scheduled, the orchestrator can sync its stable source identity into the engine and bind the exact Calendar event:

```text
source_system + source_id
        -> task_engine_id
        -> calendar_event_id
        -> followup_due_at = scheduled_end + 60 minutes
```

A follow-up worker can then query:

```text
followup_status = pending
AND followup_due_at <= now
```

This avoids attendee heuristics, title parsing, fuzzy one-hour windows, and duplicate follow-ups after resolution.

## Miss handling

A miss is evidence, not an instruction to blindly copy a block to tomorrow.

Default behavior:

1. increment attempt/miss state;
2. classify the execution as `needs_reschedule` or `needs_review`;
3. score realistic candidate windows inside the planning horizon;
4. after repeated low-stakes misses, stop automatic rescheduling and return it for planner review;
5. fixed/external commitments are never auto-rescheduled by this service;
6. any canonical action mutation is applied through `llm4life.actions`, not only inside the Task Engine.

The v1 planner is deterministic and auditable. A higher-level LLM may reason about candidate windows before calling it, but execution state does not depend on one AI vendor.

## Durable event outbox

State changes emit idempotent outbox events such as:

- `task.synced`
- `calendar.binding.created`
- `task.completed`
- `task.needs_reschedule`
- `task.needs_review`

Consumers may publish these to ChatGPT, Slack, Discord/OpenClaw, or another orchestrator. This keeps execution lifecycle independent from the notification vendor.

## Runtime

Implementation lives at:

```text
services/task-engine/
```

Current stack:

- Python 3.12+
- FastAPI
- SQLAlchemy
- PostgreSQL target / SQLite zero-setup development
- Alembic migrations
- Docker Compose local stack
- optional bearer-token protection

The service is **not currently deployed**. Current production personal-action state remains in Neon, with Google Tasks as its projection and Google Calendar as execution time.

## Security

The implementation may be public; **runtime state may not**.

Never commit:

- the runtime database;
- `.env`;
- API tokens;
- source-system credentials;
- private task data;
- private Calendar/message payloads.

The service intentionally avoids broad provider OAuth in v1. Existing authorized orchestration layers supply external event IDs and candidate windows.

## Migration plan

### Phase 0 — current production architecture

Neon `llm4life.actions` is canonical. Google Tasks projects personal actions. Google Calendar owns scheduled execution.

### Phase 1 — shadow coordination

If the Task Engine is deployed, shadow only new execution bindings. Do not migrate canonical action ownership away from Neon.

### Phase 2 — engine-driven follow-up

Use `/v1/followups/due` for explicit execution bindings while resolving canonical action state back through `llm4life.actions` and updating Calendar through supported integrations.

### Phase 3 — narrow adapters only

Add adapters only where they remove proven friction. Google Tasks remains a projection/client rather than a second canonical backlog.

### Phase 4 — replaceable notification delivery

Consume outbox events through whichever channel is strongest at the time. The Task Engine remains unchanged if the AI or notification vendor changes.

## Success criteria

The system is successful when:

- every scheduled execution can be traced to one canonical source item;
- every eligible execution block has exactly one follow-up lifecycle;
- follow-ups are not lost because of Calendar shape or watcher timing;
- missed actions produce durable behavioral evidence;
- rescheduling remains realistic and bounded;
- changing AI vendors does not erase lifecycle state;
- Calendar remains an execution surface rather than a shadow backlog;
- the Task Engine never competes with Neon for canonical personal-action ownership.
