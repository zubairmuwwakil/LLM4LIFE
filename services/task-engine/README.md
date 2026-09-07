# LLM4LIFE Task Engine

A small execution-coordination service for LLM4LIFE. Calendar is useful for scheduled execution, but it is a poor database for durable execution identity, retries, follow-up due state, deduplication, and behavioral evidence.

## Ownership boundary

The Task Engine **does not replace** canonical action systems.

- Neon `llm4life.actions` owns canonical personal action/backlog state.
- Google Tasks is the human-facing projection/capture client for personal actions.
- Jira owns engineering backlog/work.
- Google Calendar owns scheduled execution time.
- Task Engine owns execution coordination metadata: source identity, attempts/misses, Calendar bindings, follow-up due state, idempotency, orchestration-command handoff, reschedule recommendations, and an outbound event queue.
- The AI orchestrator owns reasoning, prioritization, and user interaction.

The production boundary is intentionally strict:

```text
AI / ChatGPT
  decides WHAT should happen
        |
        v
Task Engine command ledger
  persists the decision exactly once
  rejects stale/conflicting decisions
  emits durable side-effect requests
        |
        v
deterministic workers/adapters
  perform Calendar + canonical-state mutations
  report success/failure back to Task Engine
```

The AI should not replay a multi-step Calendar/Neon transaction protocol from prose. It submits one narrow, idempotent command and the deterministic layer owns execution semantics.

## Why this prevents missed follow-ups

Instead of scanning Calendar for events that merely "look like tasks," the engine creates an explicit Calendar binding whenever a canonical action is scheduled:

```text
canonical action -> Task Engine task ID -> Calendar event ID
                                      -> followup_due_at = event_end + 60m
```

The follow-up worker queries only:

```text
followup_status = pending AND followup_due_at <= now
```

No attendee heuristics. No title parsing. No fuzzy one-hour search window. No duplicate follow-up after resolution.

## API flow

### 1. Idempotently register/sync a canonical action

```http
POST /v1/tasks/sync
```

Use `(source_system, source_id)` as the stable idempotency key. For personal actions, the source should resolve back to the canonical Neon action identity rather than treating Google Tasks as canonical.

### 2. Schedule it on Calendar, then bind the external event

```http
POST /v1/tasks/{task_id}/calendar-bindings
```

The engine persists the exact external Calendar event ID and calculates the follow-up time.

### 3. Ask only for due follow-ups

```http
GET /v1/followups/due
```

### 4. Resolve the answer exactly once

```http
POST /v1/followups/{binding_id}/resolve
{"result":"completed"}
```

or

```json
{"result":"missed"}
```

A resolved binding cannot be resolved again. Canonical personal-action state still needs to be reconciled back to Neon `llm4life.actions`.

### 5. Ask the planner for the best realistic slot

```http
POST /v1/tasks/{task_id}/plan
```

Pass already-open Calendar windows. The engine rejects impossible windows, respects the movable-work window and planning horizon, scores urgency/consequence/retry pressure, and stops blindly rescheduling low-value work after repeated misses.

### 6. Submit the AI decision to the control plane

```http
POST /v1/tasks/{task_id}/commands
```

Example:

```json
{
  "command_key": "daily-planner:action-123:miss-20260907T140000Z",
  "command_type": "reschedule",
  "expected_task_version": 4,
  "requested_by": "chatgpt",
  "reason": "Still valuable; same-day capacity exists.",
  "desired_start": "2026-09-07T14:00:00-04:00",
  "desired_end": "2026-09-07T14:30:00-04:00",
  "metadata": {"source": "daily_planner"}
}
```

Supported decision types are `complete`, `reschedule`, `wait`, `cancel`, `defer`, and `status_check`.

Guarantees:

- `command_key` is globally unique and makes retries idempotent.
- `expected_task_version` rejects stale AI decisions before a side effect is requested.
- fixed tasks reject AI reschedule commands.
- the command is persisted before any Calendar/canonical-state side effect.
- exactly one durable outbox request is emitted per accepted command.
- reusing a command key for different semantics returns a conflict instead of guessing.

The command remains `accepted` until a deterministic worker performs the requested side effects.

### 7. Worker reports command completion

```http
POST /v1/commands/{command_id}/complete
```

Success:

```json
{
  "success": true,
  "result": {
    "calendar_updated": true,
    "canonical_updated": true
  }
}
```

Failure:

```json
{
  "success": false,
  "result": {},
  "error": "calendar adapter unavailable"
}
```

Completion is itself idempotent. A contradictory late completion is rejected with `409`.

### 8. Consume durable domain events

```http
GET /v1/outbox
POST /v1/outbox/{event_id}/ack
```

Accepted commands emit type-specific requests such as:

```text
orchestration.reschedule.requested
orchestration.complete.requested
orchestration.wait.requested
```

Workers consume those requests, perform narrow external mutations, and acknowledge both the command and the outbox delivery. This lets ChatGPT, OpenClaw, Slack, Discord, or another future orchestrator use the same deterministic execution state without coupling correctness to one AI vendor or prompt.

## Production invariant

For any user-visible action transition:

```text
AI decision
  -> durable command exists
  -> side effect requested once
  -> deterministic worker applies it
  -> command completed/failed
  -> audit/outbox state remains replayable
```

A Calendar mutation with no corresponding durable command is treated as a legacy/reconciliation path, not the normal production path.

## Local development

```bash
uv sync --dev
uv run pytest -q
uv run uvicorn task_engine.main:app --reload --port 8080
```

SQLite is the zero-setup default. PostgreSQL is the production target.

## Docker + PostgreSQL

```bash
cp .env.example .env
# Set TASK_ENGINE_API_TOKEN and a non-demo POSTGRES_PASSWORD before exposing beyond localhost.
docker compose up --build
```

The API binds to `127.0.0.1:8080` by default in Compose.

Run migrations:

```bash
TASK_ENGINE_DATABASE_URL='postgresql+psycopg://...' alembic upgrade head
```

## Security

- Never commit production credentials or the production database.
- Set `TASK_ENGINE_API_TOKEN` in deployed environments; clients send `Authorization: Bearer <token>`.
- Keep the service private/local or behind TLS + an authenticated reverse proxy.
- Treat task titles/notes as private runtime data even though the implementation is public.
- Connect external providers through narrow workers/adapters; do not give the reasoning layer broad write permissions it does not need.

## Deliberate limits

- No LLM inside the service. Planning/reasoning stays outside and is auditable through commands.
- No automatic deletion of source tasks or fixed commitments.
- No shadow copy of full canonical action/Jira state.
- No authority over Google Tasks; Google Tasks remains a projection/client of the personal action domain.
- External side effects remain adapter-driven: Task Engine persists/guards commands and emits durable requests; dedicated workers perform provider mutations.

These limits are intentional: make execution coordination reliable without creating another source of truth or allowing a prompt to become the transaction engine.
