# LLM4LIFE Task Engine

A small coordination-state service for LLM4LIFE. It fixes a specific failure mode: Calendar blocks are useful for execution, but Calendar is a poor database for task identity, completion state, retries, deduplication, and behavioral evidence.

## Ownership boundary

The Task Engine **does not replace** Things, Jira, or other canonical sources.

- Things / Jira / another source owns the task's real backlog content.
- Google Calendar owns scheduled execution time.
- Task Engine owns cross-system orchestration metadata: source identity, execution lifecycle, attempts/misses, Calendar bindings, follow-up due state, idempotency, reschedule recommendations, and an outbound event queue.
- The AI orchestrator owns reasoning and routing.

This keeps `one owner per responsibility` while giving the orchestrator durable state that Calendar and chat automations cannot reliably provide.

## Why this prevents missed follow-ups

The old approach asks an LLM to scan Calendar for events that "look like tasks" and ended "about an hour ago." That is inherently fuzzy.

The engine instead creates an explicit Calendar binding whenever a task is scheduled:

```text
canonical task -> Task Engine task ID -> Calendar event ID
                                      -> followup_due_at = event_end + 60m
```

The follow-up worker queries only:

```text
followup_status = pending AND followup_due_at <= now
```

No attendee heuristics. No title parsing. No one-hour fuzzy search window. No duplicate follow-up after resolution.

## API flow

### 1. Idempotently register/sync a canonical task

```http
POST /v1/tasks/sync
```

Use `(source_system, source_id)` as the stable idempotency key. Repeated syncs update the same coordination record.

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

A resolved binding cannot be resolved again.

### 5. If missed, ask the planner for the best realistic slot

```http
POST /v1/tasks/{task_id}/plan
```

Pass already-open Calendar windows. The engine rejects impossible windows, respects the movable-work window and 7-day horizon, scores urgency/consequence/retry pressure, and stops blindly rescheduling low-value work after repeated misses.

### 6. Consume durable domain events

```http
GET /v1/outbox
POST /v1/outbox/{event_id}/ack
```

This lets ChatGPT, OpenClaw, Slack, Discord, or another future orchestrator consume the same state transitions without coupling the database to one AI vendor.

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
- Connect external providers through the AI/orchestrator or narrow adapters; do not give this service broad account permissions it does not need.

## Deliberate v1 limits

- No direct Google OAuth implementation. The orchestrator already has Calendar connectivity and supplies event IDs/open windows. This avoids a second broad Calendar credential path.
- No LLM inside the service. Planning is deterministic and auditable; higher-level AI can add reasoning before submitting candidate windows.
- No automatic deletion of source tasks or fixed commitments.
- No shadow copy of full Jira/Things backlog state.

These limits are intentional: make the durable state machine reliable first, then add thin provider adapters only where they remove real friction.
