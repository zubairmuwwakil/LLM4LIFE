# Runtime Status

_Last updated: 2026-09-03_

This file describes **what is actually live now**. Long-term target ownership is defined by `config/domains.yaml`, `system.yaml`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

LLM4LIFE v2 is live with Neon as durable machine state, Google Tasks as the human action projection, Google Calendar as the execution schedule, and Product Tracker as the specialized personal-care inventory service.

Product Tracker **Cloudflare Phase 2 is now production-verified**: the Worker is deployed, authenticated reads work, Notion webhooks are signed/accepted, webhook receipts are durable in Neon, Cloudflare Queue processes them, the protected reconciliation relay is clean, and Worker database access is hardened through Cloudflare Hyperdrive using a dedicated least-privilege Neon runtime role.

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
                         Notion transitional UI
```

## Verified planning state

- Neon `llm4life.actions` is canonical personal action/backlog state.
- Google Tasks is production-live as the human-facing task projection/capture surface.
- Google Tasks Worker v0.2.0 manual and scheduled syncs have succeeded.
- Google Calendar owns scheduled execution and fixed commitments.
- Notion planning databases are rollback/reference only.

## Product Tracker production state

### Data mirror

Verified in Neon `product_tracker`:

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
Notion / ChatGPT / clients
          |
          v
 Cloudflare Worker
 API + webhook ingress
          |
          v
      Hyperdrive
          |
          v
         Neon
 canonical inventory/events
 outbox + webhook receipt ledger
          |
          v
 Cloudflare Queue
 async processing/retries
```

Verified after Hyperdrive deployment:

- `GET /health` succeeds;
- authenticated `GET /v1/needs` returns the 25-Need production snapshot;
- protected `/internal/relay` returns clean `webhooks: 0, outbox: 0` when no work is pending;
- Notion `page.properties_updated` events reach the Worker;
- signed webhook events are persisted in `WebhookReceipt`;
- Queue processing completes on the first attempt with no `lastError`;
- a reversible post-Hyperdrive Notion edit and its restoration were both received and processed successfully;
- dedicated Neon role `product_tracker_runtime` is used through Hyperdrive instead of the owner credential;
- production Prisma baseline is recorded.

### Current ownership boundary

Neon/Product Tracker is the **target canonical personal-care inventory owner**, but Notion remains a transitional human control/projection surface until the remaining mutation/retry cutover gates are intentionally tested.

Do **not** silently dual-write around Product Tracker.

## Remaining Product Tracker cutover gates

Before demoting Notion to projection/rollback-only, intentionally verify:

1. duplicate/retried `POST /v1/inventory/events` requests create exactly one canonical inventory event;
2. an outbound Notion projection is produced from a real intentional inventory mutation;
3. retry behavior does not duplicate canonical events or side effects;
4. reconciliation recovers a deliberately pending durable delivery row;
5. DLQ/retry observability is confirmed.

After these pass, route all human/agent personal-care inventory mutations through Product Tracker and make Notion optional projection/rollback UI.

## Runtime paths

| System | Status | Role |
|---|---|---|
| ChatGPT / LLM4LIFE | Live | Control plane / orchestration |
| Neon | Live | Durable machine state + Product Tracker canonical database |
| Google Tasks | Production-live | Human action projection/capture |
| Google Calendar | Live | Execution schedule and commitments |
| Cloudflare | Production-live | Google Tasks sync + Product Tracker Worker/Queue/Hyperdrive runtime |
| Product Tracker | Phase 2 production-verified | Specialized personal-care inventory service |
| Notion | Transitional | Planning rollback; inventory control/projection until final cutover gates |
| InUnity | MCP live/read-verified | Finance domain |
| Obsidian | Partial | Narrative/relationship knowledge; live bridge pending |
| Google Contacts | Migration incomplete | Preferred future canonical contact identity after dedup |
| Jira / ORC / GitHub | Live by domain | Engineering backlog / coding orchestration / code truth |

## Next priorities

### P0 — Finish Product Tracker write cutover

Run the remaining idempotency, outbound projection, retry/reconciliation, and DLQ tests above. Then demote Notion from inventory source-of-truth responsibilities.

### P1 — Remaining Notion cleanup

Remove Shopping Needs / Personal Care Products from live-source responsibilities after the Product Tracker cutover is complete while retaining useful dashboard/rollback views if desired.

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
