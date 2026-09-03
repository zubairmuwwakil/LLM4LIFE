# Runtime Status

_Last updated: 2026-09-03_

This file describes **what is actually live now**. Target ownership is defined by `config/domains.yaml`, `system.yaml`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

The v2 Neon backend is live, personal action/planning state is canonical in Neon, Google Tasks is **production-live on Worker v0.2.0**, and the personal-care inventory domain has a **parity-verified Product Tracker mirror in Neon**.

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
- Product Tracker runtime target revised to Vercel + event-driven durable async processing; hosted runtime cutover remains pending;
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
- **Neon `action_executions`** -> scheduling/execution telemetry.
- **Neon `adaptive_rules`** -> learned scheduling overrides.
- **Neon `action_receipts`** -> meaningful autonomous-action audit metadata.
- **Notion planning databases** -> rollback/reference only.

## Personal-care inventory migration

### Why Product Tracker instead of generic shopping tables

LLM4LIFE's generic `shopping_items` model is appropriate for ordinary lists, but personal-care inventory needs richer domain semantics: stable Need/SKU identity, current backup/open-unit balances, append-only inventory events, reorder policy, derived urgency, Notion reconciliation, and idempotent agent writes.

Therefore the target ownership is:

```text
ChatGPT / clients / Notion webhook
             |
             v
      Product Tracker API
             |
             v
Neon project: llm4life
Database: product_tracker
  InventoryNeed
  Product
  InventoryBalance
  InventoryEvent
  Outbox/dispatch metadata
  WebhookReceipt
             |
             v
 durable async projection/retry
             |
             v
 Notion projection / future clients
```

The database mirror is live and verified, but **this is intentionally not the write cutover yet**.

Verified mirror state:

- 25 active Needs;
- 26 active Products;
- 26 balances;
- 26 import baseline events;
- zero orphan Products;
- zero orphan balances;
- zero balance-vs-baseline mismatches.

The 25/26 relationship is expected: one functional Need has two active Product/SKU relations.

Product Tracker's derived inventory rules currently classify the mirrored Needs as 5 `BUY_NOW`, 1 `RESTOCK`, and 19 `STOCKED`. Notion's visible `Alert State` is not used as canonical truth; urgency is recalculated from balances and policy.

### Product Tracker runtime target

The adopted target is **Vercel Functions + Neon + durable Vercel queue/workflow-style event processing**, not a permanent Render/polling worker design.

The existing polling loop may remain temporarily during refactoring, but the target normal path is event-driven:

1. API/webhook receives an event;
2. Neon transaction records canonical state/event + durable work intent;
3. durable async consumer performs external projection/side effects;
4. retry is idempotent;
5. reconciliation handles missed external events/drift.

Do not use frequent Vercel Hobby Cron simply to emulate a long-running worker.

See `docs/decisions/2026-09-03-product-tracker-runtime.md`.

### Inventory cutover gate

Notion remains the live personal-care control/source surface until the hosted Product Tracker runtime passes all of these checks:

1. `/health` succeeds;
2. authenticated `GET /v1/needs` matches the Neon mirror;
3. an API mutation records exactly one durable inventory event under retries;
4. a Notion webhook reaches the service, authenticates, deduplicates, and is processed;
5. durable async projection succeeds back to Notion or another target;
6. retry/idempotency behavior does not duplicate inventory events or side effects;
7. reconciliation can detect/recover missed events or drift;
8. only then route all human/agent inventory mutations through Product Tracker and make Notion projection/rollback-only.

The production schema was initialized before Prisma migration history existed. Before any normal production `prisma migrate deploy`, run the repository's one-time `npm run db:baseline` command against the `product_tracker` production database.

## Google Tasks production state

The live Worker is deployed as `llm4life-google-tasks-sync` with a `*/15 * * * *` Cron Trigger.

Verified production state:

- Worker health reports `version: 0.2.0`;
- 17 Neon actions total;
- 14 Google Tasks projection bindings in `external_refs`;
- both Google sync checkpoints present;
- `google-tasks-sync` job enabled;
- v0.2.0 manual sync succeeded;
- a subsequent v0.2.0 scheduled cron also succeeded;
- latest job/checkpoint metadata records `worker_version: 0.2.0`.

## Active planning automations

The following live automations use Neon canonical action state:

1. **Daily Planning Loop** — 7:30 AM + 7:30 PM.
2. **Calendar Task Follow-Up** — hourly condition watch.
3. **Weekly Systems Review** — Friday around 5 PM.

The Weekly Systems Review may continue reading Notion Shopping Needs during the inventory mirror/runtime-verification phase. Do **not** switch it to Product Tracker as the authoritative inventory source until the runtime cutover gate passes.

Legacy Calendar events remain compatible:

- new blocks use `[LLM4LIFE:ACTION_ID=<uuid>]` where possible;
- existing `[LLM4LIFE:TASK_URL] <notion-url>` markers may still resolve through `external_refs`;
- Notion task records are identifiers/rollback sources, not canonical task state.

## Runtime paths

| System | Runtime status | Current role / limitation |
|---|---|---|
| GitHub | Connected, read/write verified | Architecture/config/code repository operations |
| Neon | **Connected/live** | Canonical personal actions + host for dedicated Product Tracker database |
| ChatGPT Automations | Connected/live | Planner/follow-up/review use Neon action state; inventory review remains transitional |
| Google Tasks | **Production-live v0.2.0** | Human action client/projection; Neon remains canonical |
| Cloudflare | **Production-live Worker runtime** | Google Tasks sync every 15 minutes |
| Google Calendar | Connected | Execution schedule and commitments |
| Product Tracker | **Production mirror live; hosted runtime pending** | Target personal-care inventory owner; Vercel/event-driven runtime not yet deployed/verified |
| Vercel | User stack / target runtime for Product Tracker | Do not claim Product Tracker runtime live until deployment is verified |
| Notion | Transitional | Planning is rollback-only; personal-care inventory remains live control until Product Tracker runtime verification |
| InUnity | **MCP integration complete / recently read-verified** | Consolidated finance system |
| Gmail | Connected capability | Email/source context and supported actions |
| Slack | Connected capability | Work communication/context |
| Google Contacts | Connector available; migration not done | Preferred canonical address book after Apple/Google dedup |
| Apple Contacts | User-live | Intended synced client after contact migration |
| Obsidian | Partial | Narrative/relationship knowledge; trusted live local bridge remains unimplemented |
| Jira / Atlassian | Connector available; verify per task | Canonical engineering backlog |
| ORC | External subsystem | Coding-agent orchestrator |

## Next implementation priorities

### P0 — Refactor and deploy Product Tracker runtime

1. fix the current Product Tracker CI dependency/audit issue without bypassing the security gate;
2. record the existing production migration with `npm run db:baseline` once;
3. make the Fastify API Vercel-compatible while keeping domain logic portable;
4. replace normal infinite polling with durable Vercel async queue/workflow consumers;
5. preserve a DB outbox/dispatch record where needed to avoid a transaction-vs-publish dual-write race;
6. deploy to Vercel using secrets outside Git;
7. verify `/health` and authenticated `/v1/needs`;
8. verify API mutation idempotency;
9. verify Notion webhook ingestion/deduplication;
10. verify async projection/retries and reconciliation;
11. then cut personal-care inventory writes over to Product Tracker and demote Notion to projection/rollback.

### P1 — Remaining Notion cleanup

After Product Tracker cutover:

- remove Shopping Needs from Notion's live-source responsibilities;
- keep useful Notion pages only as projection/rollback/dashboard surfaces;
- retain historical AI Activity Log only where it provides useful audit/reference value.

### P1 — Live Obsidian bridge

Desired path:

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

### P1 — Contacts consolidation

Deduplicate Apple + Google Contacts before making Google Contacts canonical.

### P1 — Household operations

Populate generic household/vehicle asset + maintenance state in LLM4LIFE; keep personal-care inventory inside Product Tracker rather than flattening it into generic shopping rows.

See `docs/LONG_TERM_ROADMAP.md` for the complete long-term sequence beyond these immediate priorities.

## Scheduling runtime

Current defaults remain:

- sleep 11:00 PM–7:00 AM protected;
- weekday work 9:00 AM–1:00 PM soft-busy;
- movable personal work defaults to 1:00 PM–9:00 PM America/Toronto;
- leave buffer;
- hard commitments are not moved for optimization;
- waiting work does not occupy execution time;
- date-only deadlines/follow-ups remain date-only;
- repeated misses are evidence for replanning, not an instruction to endlessly push work forward.

## Public repository constraint

Public repositories contain architecture, contracts and schemas only. Never commit actual database URLs, OAuth credentials, refresh tokens, Notion tokens/webhook secrets, private inventory payloads, private task payloads, private contact/relationship details, health records, financial identifiers, confidential work content, or private message bodies.
