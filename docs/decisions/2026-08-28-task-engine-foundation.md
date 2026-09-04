# 2026-08-28 — Add a task execution coordination engine

**Status:** Implementation retained; not deployed. Ownership wording updated 2026-09-04 to match newer LLM4LIFE decisions.

## Decision

Introduce a small LLM4LIFE Task Engine for **optional cross-system execution lifecycle state**.

The newer canonical ownership model takes precedence:

- Neon `llm4life.actions` is canonical for personal action/backlog state.
- Google Tasks is the human-facing projection/capture client for personal actions.
- Jira remains canonical for engineering backlog/work.
- Google Calendar remains canonical for scheduled execution/time.
- AI remains the reasoning/routing/planning layer.
- Task Engine may own only execution coordination metadata: stable source identity, execution attempts/misses, Calendar bindings, follow-up due state, idempotency, reschedule/review state, and a durable event outbox.

The Task Engine must never become a second canonical personal backlog.

## Why

Calendar follow-up automation can otherwise be forced to infer whether events are task-style work and whether they fall inside fuzzy timing windows. Calendar titles/descriptions are also the wrong place for retry history and execution lifecycle state.

## Invariant

Whenever a canonical action is deliberately scheduled for execution, an optional explicit binding may be created:

```text
canonical source item -> task_engine_id -> exact calendar_event_id
```

The Task Engine calculates `followup_due_at`. Follow-up workers can query due bindings rather than rediscovering task events heuristically.

Any resulting canonical personal-action state change still flows through `llm4life.actions`; Google Tasks remains its projection.

## Rescheduling rule

A miss increments durable evidence. Movable work can be proposed for a realistic future slot, but repeated low-stakes misses stop automatic rescheduling and require planner reassessment. Fixed/external commitments are never auto-moved by this service.

## Vendor independence

The service deliberately contains no LLM dependency. It exposes a narrow HTTP API and durable outbox so ChatGPT, OpenClaw, local models, Slack/Discord consumers, or future orchestrators can use the same execution lifecycle state.

## Security boundary

Generic implementation code may live in this public repository. Runtime databases, secrets, private task content, credentials, tokens, and private Calendar/message data must never be committed.

The first version avoids introducing another broad provider OAuth path. Existing authorized orchestration layers supply Calendar event IDs and candidate free windows.

## Rollout

1. Keep Neon actions + Google Tasks + Google Calendar as the production ownership model.
2. If useful, deploy Task Engine privately in shadow mode for new execution bindings.
3. Switch follow-ups to explicit due bindings only after observed reliability.
4. Keep canonical action mutation in Neon and provider clients as projections.
5. Add only narrow adapters that prove useful.
6. Keep notification consumers replaceable through the outbox.

## Supersedes / clarifies

The original 2026-08-28 wording that named Things 3 as canonical personal backlog is superseded by the later Neon/Google Tasks architecture. The execution-coordination idea remains valid, but the Task Engine is subordinate to the current canonical action domain.
