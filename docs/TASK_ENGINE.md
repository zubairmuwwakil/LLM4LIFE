# Task Engine

_Status: implementation ready for review; not yet deployed_

## Problem

The current Calendar follow-up loop infers whether an event is a task by inspecting event shape, title, attendees, and timing. That is useful as a temporary bridge but cannot be made fully reliable: a user-owned task can look like a meeting, an hourly watcher can drift across fuzzy time windows, and Calendar titles/descriptions are not a durable task state machine.

A missed personal task follow-up exposed this gap.

## Decision

Add a small **Task Engine** as a coordination-state service between canonical task sources and the execution calendar.

It does **not** become the personal or engineering backlog.

```text
Things / Jira / other canonical source
              |
              | stable source identity
              v
        LLM4LIFE Task Engine
     lifecycle + attempts + bindings
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

## Ownership boundary

| Responsibility | Owner |
|---|---|
| Personal backlog/content | Things 3 |
| Engineering backlog/content | Jira |
| Scheduled execution/time | Google Calendar |
| Cross-system execution lifecycle | Task Engine |
| Reasoning, routing, prioritization | AI orchestrator |
| Work/personal communication | Slack / Discord when connected |

The Task Engine owns only coordination metadata that cannot reliably live in one external tool: source identity, attempts/misses, Calendar bindings, due follow-ups, idempotency, lifecycle status, and durable domain events.

## Deterministic follow-up

When a canonical task is scheduled, the orchestrator first/also syncs its source identity into the engine and then binds the exact Calendar event:

```text
source_system + source_id
        -> task_engine_id
        -> calendar_event_id
        -> followup_due_at = scheduled_end + 60 minutes
```

The watcher no longer asks Calendar which events "look like tasks." It asks the Task Engine:

```text
followup_status = pending
AND followup_due_at <= now
```

This provides:

- no self-attendee/meeting-classification ambiguity;
- no fuzzy "about one hour ago" boundary;
- no duplicate follow-up after a binding is handled;
- exact relationship between the source task and its execution block;
- durable attempt/miss evidence even when the Calendar block is moved.

## Miss handling

A miss is evidence, not an instruction to blindly copy a block to tomorrow.

Default behavior:

1. increment attempt/miss state;
2. classify the task as `needs_reschedule` or `needs_review`;
3. for movable work, score realistic candidate windows inside the planning horizon;
4. after repeated low-stakes misses, stop auto-rescheduling and return it for planner review;
5. higher-consequence tasks may continue to receive a proposed slot;
6. fixed/external commitments are never auto-rescheduled by this service.

The current v1 planner is deterministic and auditable. A higher-level LLM may reason about candidate windows before calling it, but task state does not depend on one AI vendor.

## Durable event outbox

State changes emit idempotent outbox events such as:

- `task.synced`
- `calendar.binding.created`
- `task.completed`
- `task.needs_reschedule`
- `task.needs_review`

A consumer can publish these to ChatGPT, Slack, Discord/OpenClaw, or another future orchestrator and acknowledge them afterward. This avoids coupling lifecycle state to the notification vendor.

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

## Security

The implementation may be public; **runtime state may not**.

Never commit:

- the database;
- `.env`;
- API tokens;
- source-system credentials;
- private task data exported from production;
- private Calendar/message payloads.

The service intentionally does not implement broad Google OAuth in v1. The already-authorized orchestrator supplies external event IDs and open candidate windows, reducing credential surface area.

## Migration plan

### Phase 0 — temporary bridge

Keep the Calendar watcher, but make it less brittle: self-only attendees do not imply a meeting, use an overlapping deterministic catch-up window, deduplicate with markers, and never move fixed external events.

### Phase 1 — shadow coordination

Deploy Task Engine privately. New task blocks receive explicit task IDs and Calendar bindings. The existing watcher can remain as fallback while the engine is observed.

### Phase 2 — engine-driven follow-up

Change the follow-up automation to read `/v1/followups/due` rather than scanning Calendar heuristically. Resolve answers into the engine, then update canonical source/Calendar through their supported connectors.

### Phase 3 — canonical adapters

Add only thin adapters that prove useful, for example a supported Things bridge or Jira connector synchronization. Do not mirror entire backlogs into the engine.

### Phase 4 — notification delivery

Consume outbox events through whichever channel is strongest at the time. The Task Engine remains unchanged if ChatGPT, Slack, Discord, OpenClaw, or a local LLM is replaced.

## Success criteria

The system is successful when:

- a scheduled task can always be traced to one canonical source item;
- every eligible execution block has exactly one follow-up lifecycle;
- follow-ups are not lost because of Calendar shape or watcher timing;
- missed tasks produce durable behavioral evidence;
- rescheduling remains realistic and bounded;
- changing AI vendors does not erase task lifecycle state;
- Calendar remains an execution surface rather than a shadow backlog.
