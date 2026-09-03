# Runtime Status

_Last updated: 2026-09-03_

This file describes **what is actually live now**. Long-term target ownership is defined by `config/domains.yaml`, `system.yaml`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

LLM4LIFE v2 is live with Neon as durable machine state, Google Tasks as the human action projection, Google Calendar as the execution schedule, and Product Tracker/Neon as the canonical personal-care inventory service.

Product Tracker Phase 2 reliability and write cutover are complete. The production Cloudflare Worker uses Hyperdrive and invocation-scoped Prisma database clients, API idempotency/retry/reconciliation gates passed, Cloudflare retry→DLQ behavior was verified in isolated staging, and production runs with Notion inbound inventory sync disabled.

## Current architecture

```text
                         ChatGPT / LLM4LIFE
                                |
            +-------------------+-------------------+
            |                   |                   |
            v                   v                   v
         Neon             Google Calendar      Domain systems
   durable machine state     execution time    Jira/GitHub/ORC,
            |                                     InUnity, etc.
            |
      +-----+-------------------+
      |                         |
      v                         v
Google Tasks              Product Tracker
human action UI           personal-care inventory
      |                         |
Cloudflare Worker         Cloudflare Worker
15-min sync               + Queue + Hyperdrive
                                |
                                v
                              Neon
                     canonical inventory/events
                                |
                                v
                         Notion projection/UI
```

## Verified planning state

- Neon `llm4life.actions` is canonical personal action/backlog state.
- Google Tasks is production-live as the human-facing task projection/capture surface.
- Google Calendar owns scheduled execution and fixed commitments.
- Notion planning databases are rollback/reference only.
- Personal-care inventory is canonical in Neon database `product_tracker`, owned through the Product Tracker domain service.

## Product Tracker production state

### Baseline

Verified in Neon `product_tracker` at migration baseline:

- 25 active Needs;
- 26 active Products;
- 26 balances;
- 26 baseline inventory events;
- zero orphan Product/balance relationships;
- zero balance-vs-baseline mismatches;
- derived inventory health: 5 `BUY_NOW`, 1 `RESTOCK`, 19 `STOCKED`.

The 25/26 relationship is expected because one functional Need has two active SKUs.

### Runtime

Live Worker:

```text
llm4life-product-tracker
```

Production path:

```text
ChatGPT / clients
      |
      v
Cloudflare Worker
 authenticated API
      |
      v
  Hyperdrive
      |
      v
     Neon
 canonical inventory/events
 outbox + webhook receipts
      |
      v
Cloudflare Queue
 retries + reconciliation
      |
      v
Notion projection
```

Verified cutover behavior:

- `GET /health` succeeds and reports Product Tracker `v0.3.0` with `notionInboundSyncEnabled=false` at canonical cutover;
- authenticated `GET /v1/needs` returns the production snapshot;
- protected `/internal/relay` is clean when no durable work is pending;
- duplicate/retried API mutations create exactly one canonical InventoryEvent;
- outbound Neon → Notion projection works;
- application-side failures use durable backoff and become terminal `FAILED` at attempt 8;
- reconciliation recovered deliberately pending durable work without duplicate Notion side effects;
- deliberate staging queue-handler crashes were retried by Cloudflare and delivered to the DLQ;
- Worker database access uses Hyperdrive and the dedicated least-privilege Neon role `product_tracker_runtime`;
- Prisma/pg clients are invocation-scoped in Workers after a cross-request I/O bug was caught during staging.

### Ownership boundary

Product Tracker/Neon is the **canonical personal-care inventory owner**.

Production sets `NOTION_INBOUND_SYNC_ENABLED=false`. Signed Notion webhook calls remain authenticated/acknowledged but do not mutate Neon. Notion Shopping Needs and Personal Care Products are projection/reference/rollback surfaces only.

All human/agent personal-care inventory mutations must route through Product Tracker domain events. Do not silently dual-write or fall back to Notion when Product Tracker/Neon is unavailable.

## Reliability hardening in progress

The next production release adds durable DLQ receipts in Neon, an authenticated `/internal/status` reliability endpoint, and scheduled attention logging for failed outbox rows, overdue durable work, overdue webhook receipts and unresolved dead letters.

A narrow outbound Notion exactly-once race remains: if Notion page creation succeeds but persistence of `notionEventPageId` fails immediately afterward, retry could create a duplicate page. The planned fix is a stable Product Tracker Event ID property in Notion plus query-before-create.

## Runtime paths

| System | Status | Role |
|---|---|---|
| ChatGPT / LLM4LIFE | Live | Control plane / orchestration |
| Neon | Live | Durable machine state + Product Tracker canonical inventory database |
| Google Tasks | Production-live | Human action projection/capture |
| Google Calendar | Live | Execution schedule and commitments |
| Cloudflare | Production-live | Google Tasks sync + Product Tracker Worker/Queue/Hyperdrive runtime |
| Product Tracker | Production canonical | Specialized personal-care inventory owner |
| Notion | Transitional/auxiliary | Planning rollback + personal-care projection/reference |
| InUnity | MCP live/read-verified | Finance domain |
| Obsidian | Partial | Narrative/relationship knowledge; live bridge pending |
| Google Contacts | Migration incomplete | Preferred future canonical contact identity after dedup |
| Jira / ORC / GitHub | Live by domain | Engineering backlog / coding orchestration / code truth |

## Next priorities

### P0 — Observe Product Tracker cutover

Run the 24-hour post-cutover observation check. If health, durable retry state and projection remain clean, remove the temporary reliability Worker/Queues and temporary Neon reliability branch.

### P0 — Production reliability observability

Deploy the durable DLQ receipt migration/runtime and monitor failed outbox, overdue work, overdue webhook receipts and unresolved dead letters.

### P1 — Notion event idempotency hardening

Add a stable Product Tracker Event ID to Notion Inventory Events and query it before remote page creation.

### P1 — Remaining Notion cleanup

Retain useful dashboard/rollback views but do not restore Shopping Needs / Personal Care Products to source-of-truth responsibilities.

### P1 — Live Obsidian bridge

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

### P1 — Contacts consolidation

Deduplicate Apple + Google Contacts before making Google Contacts canonical.

### P1 — Household operations

Populate generic household/vehicle asset + maintenance state in LLM4LIFE while keeping personal-care inventory inside Product Tracker.

See `docs/LONG_TERM_ROADMAP.md` for the complete sequence.

## Public repository constraint

Public repositories contain architecture, contracts, schemas, and non-sensitive runtime metadata only. Never commit database URLs, passwords, OAuth credentials, refresh tokens, API tokens, webhook secrets, private inventory/task payloads, private relationship/contact details, health records, financial identifiers, confidential work content, or private message bodies.
