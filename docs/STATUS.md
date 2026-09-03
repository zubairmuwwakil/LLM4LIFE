# Runtime Status

_Last updated: 2026-09-03_

This file describes **what is actually live now**. Long-term target ownership is defined by `config/domains.yaml`, `system.yaml`, domain contracts such as `docs/PEOPLE.md`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

LLM4LIFE v2 is live with Neon as durable machine state, Google Tasks as the human action projection, Google Calendar as the execution schedule, and Product Tracker/Neon as the canonical personal-care inventory service.

Product Tracker Phase 2 reliability and write cutover are complete. Production is on Worker `v0.4.0`, Notion inbound inventory sync is disabled, durable reliability status/DLQ receipts are live, and the stable Product Tracker Event ID query-before-create hardening is deployed.

The next subsystem is **People / Relationships**, currently **Phase 0 documentation only**. Its target architecture is accepted, but no People Neon schema, contact import, dedup cutover or Google Contacts projection migration has been completed yet.

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
sync runtime              + Queue + Hyperdrive
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

Verified at migration baseline:

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
 dead-letter receipts
      |
      v
Cloudflare Queue
 retries + reconciliation
      |
      v
Notion projection
```

Verified cutover/reliability behavior:

- `GET /health` succeeds and reports Product Tracker `v0.4.0` with `notionInboundSyncEnabled=false`;
- authenticated reliability status reports zero failed/overdue/dead-letter work when clean;
- protected `/internal/relay` is clean when no durable work is pending;
- duplicate/retried API mutations create exactly one canonical InventoryEvent;
- outbound Neon → Notion projection works;
- application-side failures use durable backoff and become terminal `FAILED` at attempt 8;
- reconciliation recovered deliberately pending durable work without duplicate Notion side effects;
- deliberate staging queue-handler crashes were retried by Cloudflare and delivered to the DLQ;
- durable `DeadLetterEvent` persistence and reliability status are live;
- Worker database access uses Hyperdrive and the dedicated least-privilege Neon runtime role;
- Prisma/pg clients are invocation-scoped in Workers after a cross-request I/O bug was caught during staging;
- Notion Inventory Events now carries `Product Tracker Event ID`, and projection queries that stable ID before create to close the known create-then-pointer retry window for future events.

### Ownership boundary

Product Tracker/Neon is the **canonical personal-care inventory owner**.

Production sets `NOTION_INBOUND_SYNC_ENABLED=false`. Signed Notion webhook calls remain authenticated/acknowledged but do not mutate Neon. Notion Shopping Needs, Products and Inventory Events are projection/reference/rollback surfaces only.

All human/agent personal-care inventory mutations must route through Product Tracker domain events. Do not silently dual-write or fall back to Notion when Product Tracker/Neon is unavailable.

### Remaining closeout

The 24-hour post-cutover observation window and temporary reliability staging cleanup remain. These are operational closeout tasks, not ownership blockers.

## People / Relationships Phase 0

Accepted target:

```text
Neon
  stable person_id
  external references
  structured relationship machine state
  structured facts + provenance
  minimal interaction metadata
      |
      +--> Google Contacts address-book projection/client after dedup cutover
      +--> LLM4LIFE actions -> Google Tasks for follow-ups
      +--> Google Calendar for scheduled interactions

Obsidian
  narrative relationship memory
  diary/reflections
  long-form person/interaction context
```

**Not live yet:**

- no People Neon tables have been created;
- Apple/Google Contacts have not been canonically reconciled/imported;
- Google Contacts has not been cut over as a projection/client;
- no automatic People capture or relationship automation is active from this new architecture.

Current private contact/relationship material remains in existing systems during migration. Do not destructively clean or rewrite it based on target docs alone.

Read `docs/PEOPLE.md` and `docs/decisions/2026-09-03-people-subsystem-architecture.md` before People work.

## Runtime paths

| System | Status | Role |
|---|---|---|
| ChatGPT / LLM4LIFE | Live | Control plane / orchestration |
| Neon | Live | Durable machine state + Product Tracker canonical inventory database |
| Google Tasks | Production-live | Human action projection/capture |
| Google Calendar | Live | Execution schedule and commitments |
| Cloudflare | Production-live | Google Tasks sync + Product Tracker Worker/Queue/Hyperdrive runtime |
| Product Tracker | Production canonical v0.4.0 | Specialized personal-care inventory owner |
| Notion | Auxiliary | Planning rollback + personal-care projection/reference |
| InUnity | MCP live/read-verified | Finance domain |
| Obsidian | Partial | Narrative knowledge/relationship context; live bridge pending |
| Google Contacts | Connector available; People migration incomplete | Target address-book client/projection after dedup |
| Apple Contacts | Current device/source during People migration | Target synchronized device client |
| Jira / ORC / GitHub | Live by domain | Engineering backlog / coding orchestration / code truth |

## Next priorities

### P0 — Observe and close Product Tracker staging

Run the 24-hour post-cutover check. If health, durable retry state and projection remain clean, remove the temporary reliability Worker/Queues and temporary Neon reliability branch.

### P0 — People Phase 1: schema + read-only inventory

Do **not** begin with destructive contact edits.

1. Design/test the minimum People schema from `docs/PEOPLE.md`.
2. Inspect Google Contacts and the supported Apple Contacts export/integration path.
3. Build a read-only inventory and duplicate-candidate report.
4. Validate contact-field authority/conflict semantics.
5. Use synthetic fixtures only in this public repo.

### P1 — People canonical identity import

Only after Phase 1 gates pass: stable person IDs, external refs, idempotent import, conservative merge workflow and rollback.

### P1 — Live Obsidian bridge

```text
AI/router -> authenticated local adapter -> live vault -> normal vault backup/sync
```

People narrative linkage should build on this when practical rather than treating the private backup repository as the permanent real-time application API.

### P1 — Remaining Notion cleanup

Retain useful Product Tracker dashboard/rollback views but do not restore Notion to source-of-truth responsibilities.

### P1 — Household operations

Populate generic household/vehicle asset + maintenance state while keeping personal-care inventory inside Product Tracker.

See `docs/LONG_TERM_ROADMAP.md` for the broader sequence.

## Public repository constraint

Public repositories contain architecture, contracts, schemas, synthetic examples and non-sensitive runtime metadata only. Never commit database URLs, passwords, OAuth credentials, refresh tokens, API tokens, webhook secrets, private inventory/task payloads, private relationship/contact details, health records, financial identifiers, confidential work content, or private message bodies.
