# Runtime Status

_Last updated: 2026-09-04_

This file describes **what is actually live now**. Long-term target ownership is defined by `config/domains.yaml`, `system.yaml`, domain contracts such as `docs/PEOPLE.md`, and `docs/LONG_TERM_ROADMAP.md`.

## Headline

LLM4LIFE v2 is live with Neon as durable machine state, Google Tasks as the human action projection, Google Calendar as the execution schedule, and Product Tracker/Neon as the canonical personal-care inventory service.

Product Tracker Phase 2 reliability and write cutover are complete. Production is on Worker `v0.4.0`, Notion inbound inventory sync is disabled, durable reliability status/DLQ receipts are live, and the stable Product Tracker Event ID query-before-create hardening is deployed.

The **People / Relationships Phase 1 schema is now live in production Neon**. The schema and generic account-scoped external-reference model are deployed, but no real People records have been imported yet, no contacts have been merged or mutated, and Google/Apple field ownership has not been cut over.

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

## People / Relationships Phase 1

The production Neon schema now includes:

- `llm4life.people`
- `llm4life.relationships`
- `llm4life.person_facts`
- `llm4life.interactions`
- `llm4life.interaction_people`
- `llm4life.action_people`

The existing generic `llm4life.external_refs` model was reused rather than creating a separate `person_external_refs` table. It now supports provider `account_scope`, first/last-seen timestamps and archive lifecycle metadata.

**Verified immediately after deployment:**

- 0 People rows;
- 0 person facts;
- 0 interactions;
- 95 pre-existing external refs preserved.

**Still not live:**

- no real Apple/Google contact import;
- no canonical dedup/merge of real contacts;
- no Google Contacts field-authority cutover;
- no Apple Contacts synchronized-client cutover;
- no Obsidian People migration;
- no automatic People capture/relationship automation.

Current private contact/relationship material remains in existing systems during migration. Do not destructively clean or rewrite it based on target docs alone.

Read `docs/PEOPLE.md`, `docs/people/PHASE_1_REPORT.md`, and `docs/decisions/2026-09-03-people-subsystem-architecture.md` before People work.

## Runtime paths

| System | Status | Role |
|---|---|---|
| ChatGPT / LLM4LIFE | Live | Control plane / orchestration |
| Neon | Live | Durable machine state + Product Tracker canonical inventory database + deployed People schema |
| Google Tasks | Production-live | Human action projection/capture |
| Google Calendar | Live | Execution schedule and commitments |
| Cloudflare | Production-live | Google Tasks sync + Product Tracker Worker/Queue/Hyperdrive runtime |
| Product Tracker | Production canonical v0.4.0 | Specialized personal-care inventory owner |
| Notion | Auxiliary | Planning rollback + personal-care projection/reference |
| InUnity | MCP live/read-verified | Finance domain |
| Obsidian | Partial | Narrative knowledge/relationship context; live bridge pending |
| Google Contacts | Connector read-verified; full inventory path incomplete | Target address-book client; no field-authority cutover yet |
| Apple Contacts | Current device/source during People migration | Target synchronized device client |
| Jira / ORC / GitHub | Live by domain | Engineering backlog / coding orchestration / code truth |

## Next priorities

### P0 — Observe and close Product Tracker staging

Run the 24-hour post-cutover check. If health, durable retry state and projection remain clean, remove the temporary reliability Worker/Queues and temporary Neon reliability branch.

### P0 — People Phase 1: complete read-only inventory

The schema portion of Phase 1 is live. Continue with read-only inventory before any real contact mutation:

1. Obtain a complete Google saved-contact inventory using a supported enumeration path rather than query-only search.
2. Inventory Apple/iCloud contacts via a private local vCard export or supported local Contacts bridge.
3. Run the deterministic duplicate-candidate engine against private/transient normalized data.
4. Review field-preservation semantics before finalizing Google-vs-Neon mutable contact-field authority.
5. Keep public-repo fixtures synthetic only.

### P1 — People canonical identity import

Only after inventory/reconciliation gates pass: import stable person IDs and external refs idempotently, then review duplicate candidates conservatively.

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
