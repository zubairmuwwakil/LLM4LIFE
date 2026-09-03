# Runtime Status

_Last updated: 2026-09-03_

This file describes **what is actually live now**. Target ownership is defined by `config/domains.yaml`, `system.yaml`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

The v2 Neon backend is live, personal action/planning state is canonical in Neon, Google Tasks is **production-live on Cloudflare Worker v0.2.0**, and personal-care inventory has a **parity-verified Product Tracker mirror in Neon**. Product Tracker's new **Cloudflare Worker + Queue runtime is implemented and CI-green but not deployed yet**.

Implemented and verified:

- dedicated `llm4life` Neon project and production schema;
- personal planning cut over from Notion to Neon;
- Google Tasks OAuth + Cloudflare Worker v0.2.0 production-live;
- manual and scheduled Google Tasks sync verified;
- dedicated `product_tracker` database created inside the same Neon project;
- Product Tracker schema applied from the existing Prisma model;
- 25 active inventory Needs mirrored from Notion;
- 26 active Products mirrored from Notion;
- 26 balances and 26 baseline inventory events imported atomically;
- zero orphan product/balance records and zero baseline-vs-balance mismatches;
- Product Tracker Cloudflare Worker/Queue runtime committed;
- Product Tracker CI passes Prisma validation/migrations, dependency audit, typecheck/tests, and Wrangler dry-run;
- InUnity ChatGPT MCP integration completed and recently read-verified.

## Canonical planning runtime

```text
                           +--> Google Tasks
                           |    human action client
                           |
Neon/PostgreSQL actions ---+
        |                  |
        |                  +<-- Cloudflare Worker v0.2.0
        |                       15-minute sync
        |
        +--> ChatGPT planner --> Google Calendar
                                  execution/time
```

### Current planning ownership

- **Neon `llm4life.actions`** -> canonical personal action/backlog state.
- **Google Tasks** -> live human-facing action client and authorized capture/completion surface; not canonical state.
- **Cloudflare Worker** -> live Google Tasks <-> Neon projection/sync runtime.
- **Google Calendar** -> execution schedule and fixed time commitments.
- **Neon `action_executions` / `adaptive_rules` / `action_receipts`** -> execution telemetry, learned rules, and audit metadata.
- **Notion planning databases** -> rollback/reference only.

## Personal-care inventory migration

Personal-care inventory is intentionally owned by the specialized Product Tracker model rather than generic `shopping_items` because it needs stable Need/SKU identity, balances, append-only inventory events, reorder policy, derived urgency, webhook reconciliation, and idempotent writes.

Verified Neon mirror:

- 25 active Needs;
- 26 active Products;
- 26 balances;
- 26 baseline events;
- zero orphan Products/balances;
- zero balance-vs-baseline mismatches;
- derived state: 5 `BUY_NOW`, 1 `RESTOCK`, 19 `STOCKED`.

The 25/26 relationship is expected because one functional Need has two active SKUs.

### Product Tracker target runtime

```text
ChatGPT / clients / Notion webhook
              |
              v
      Cloudflare Worker
    HTTP/API/webhook ingress
              |
              v
             Neon
 canonical inventory/event state
 outbox + webhook receipt ledger
              |
              v
      Cloudflare Queue
 async projection / retries
              |
              v
 Notion projection / future effects
```

Neon remains canonical. Cloudflare is compute/ingress/queue infrastructure, not the inventory database.

The Worker implementation is committed and includes:

- `/health`;
- authenticated `/v1/needs`;
- authenticated + idempotent `/v1/inventory/events`;
- signed `/webhooks/notion` ingestion;
- Queue consumer by durable row ID;
- DLQ/retry configuration;
- protected `/internal/relay`;
- a 5-minute scheduled reconciliation relay that scans only Product Tracker's own pending delivery ledger, **not Notion**.

The database transaction remains the durable boundary. Normal work publishes to Cloudflare Queue after commit; if queue publication is missed, the durable Neon outbox/receipt row survives and the scheduled relay can republish it.

Cloudflare Workflows are optional later only if a real multi-step durable process justifies them. Hyperdrive is also a later connection optimization, not a prerequisite for first deployment.

See `docs/decisions/2026-09-03-product-tracker-runtime.md`.

### Inventory cutover gate

Notion remains the live personal-care control/source surface until all of these are verified against the deployed Cloudflare runtime:

1. `/health` succeeds;
2. authenticated `GET /v1/needs` matches the Neon mirror;
3. duplicate/retried API requests create exactly one canonical inventory event;
4. Notion webhook signature validation and deduplication work;
5. Queue processing performs outbound Notion projection;
6. retries do not duplicate events or side effects;
7. reconciliation recovers a deliberately pending durable delivery row;
8. DLQ/retry observability is confirmed;
9. only then route all human/agent inventory mutations through Product Tracker and make Notion projection/rollback-only.

The production database was initialized before Prisma migration history existed. Run the repository's one-time `npm run db:baseline` against production before normal production `prisma migrate deploy` use.

## Google Tasks production state

The live Worker is `llm4life-google-tasks-sync` with a `*/15 * * * *` Cron Trigger.

Verified:

- Worker health reports `version: 0.2.0`;
- 17 Neon actions total;
- 14 Google Tasks projection bindings;
- both Google sync checkpoints present;
- durable sync job enabled;
- manual and scheduled v0.2.0 syncs succeeded.

## Active planning automations

1. **Daily Planning Loop** — 7:30 AM + 7:30 PM.
2. **Calendar Task Follow-Up** — hourly condition watch.
3. **Weekly Systems Review** — Friday around 5 PM.

The Weekly Systems Review may continue reading Notion Shopping Needs until Product Tracker runtime cutover passes the gate above. Do not treat the Neon mirror alone as permission to demote Notion.

## Runtime paths

| System | Runtime status | Current role / limitation |
|---|---|---|
| GitHub | Connected, read/write verified | Architecture/config/code truth |
| Neon | **Connected/live** | Canonical personal actions + Product Tracker database host |
| ChatGPT Automations | Connected/live | Planning/follow-up/review execution surface |
| Google Tasks | **Production-live v0.2.0** | Human action client/projection |
| Cloudflare | **Google Tasks live; Product Tracker implementation ready** | Shared Worker/event runtime; Product Tracker deployment still pending |
| Google Calendar | Connected | Execution schedule and commitments |
| Product Tracker | **Neon mirror live; Cloudflare code CI-green; deployment pending** | Target personal-care inventory owner |
| Notion | Transitional | Planning rollback-only; inventory control remains live until Product Tracker verification |
| Vercel | User-live for fitting web workloads | No longer Product Tracker target; evaluate per project |
| InUnity | **MCP complete / recently read-verified** | Consolidated finance |
| Obsidian | Partial | Narrative/relationship knowledge; live local bridge pending |
| Google Contacts | Available; migration incomplete | Preferred canonical contact identity after dedup |
| Jira / ORC / GitHub | Available/current by domain | Engineering backlog / coding orchestration / code truth |

## Next implementation priorities

### P0 — Deploy and verify Product Tracker on Cloudflare

1. run one-time production Prisma baseline if not already recorded;
2. provision the Product Tracker Queue/DLQ;
3. set Worker secrets outside Git;
4. deploy `llm4life-product-tracker`;
5. verify health + authenticated reads;
6. verify idempotent API mutation behavior using a real intentional inventory action, not fabricated stock;
7. configure/verify Notion webhook ingestion;
8. verify Queue projection/retries/reconciliation/DLQ;
9. then cut inventory writes over and demote Notion.

### P1 — Remaining Notion cleanup

After Product Tracker cutover, remove Shopping Needs from Notion's live-source responsibilities while retaining useful projection/rollback/dashboard views.

### P1 — Live Obsidian bridge

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

### P1 — Contacts consolidation

Deduplicate Apple + Google Contacts before making Google Contacts canonical.

### P1 — Household operations

Populate generic household/vehicle asset + maintenance state in LLM4LIFE while keeping personal-care inventory inside Product Tracker.

See `docs/LONG_TERM_ROADMAP.md` for the complete long-term sequence.

## Public repository constraint

Public repositories contain architecture, contracts and schemas only. Never commit actual database URLs, OAuth credentials, refresh tokens, Notion tokens/webhook secrets, private inventory/task payloads, private contact/relationship details, health records, financial identifiers, confidential work content, or private message bodies.
